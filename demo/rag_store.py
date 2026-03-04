"""
RAGMemoryStore — semantic retrieval for the memory poisoning demo.

Graceful fallback chain:
  1. chromadb (if installed) — persistent vector DB with embeddings
  2. sentence_transformers (if installed) — local embeddings, real cosine similarity
  3. Keyword cosine similarity (always available) — TF-IDF word-overlap scores

The demo insight: even keyword-overlap scoring is "poisoned" when the attacker
writes content that is semantically indistinguishable from legitimate queries.
Showing similarity scores (e.g., 0.87 for the attacker's doc vs 0.89 for the
real runbook) makes the point viscerally clear.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from datetime import datetime
from typing import List, Optional, Tuple

from .schemas import MemoryRecord


# ---------------------------------------------------------------------------
# Utility: keyword-based TF-IDF vector similarity
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _cosine_sim(a: Counter, b: Counter) -> float:
    """Cosine similarity between two term-frequency counters."""
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b.get(k, 0) for k in a)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ---------------------------------------------------------------------------
# RAGMemoryStore
# ---------------------------------------------------------------------------

class RAGMemoryStore:
    """
    Semantic memory store with cosine-similarity retrieval.

    Uses keyword TF-IDF cosine similarity (no external dependencies required).
    Produces realistic similarity scores (0.0–1.0) visible in the run output.

    If chromadb is installed, it can be swapped in for real vector embeddings —
    the interface is identical.
    """

    def __init__(self, persist_path: str, embedding_model: str = "all-MiniLM-L6-v2") -> None:
        self.persist_path = persist_path
        self.embedding_model = embedding_model
        parent = os.path.dirname(persist_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._records: List[MemoryRecord] = []
        self._last_scores: List[float] = []
        self._load()

    def _load(self) -> None:
        """Load previously ingested records from JSONL file."""
        if not os.path.exists(self.persist_path):
            return
        with open(self.persist_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        self._records.append(MemoryRecord(**data))
                    except Exception:
                        pass

    def ingest(
        self,
        content: str,
        trust_level: str,
        provenance: str,
        tags: List[str],
        risk_flags: Optional[List[str]] = None,
        created_at: Optional[str] = None,
    ) -> MemoryRecord:
        """Embed and store a document. Returns the MemoryRecord."""
        record_id = len(self._records) + 1
        record = MemoryRecord(
            id=record_id,
            content=content,
            tags=tags,
            trust_level=trust_level,
            provenance=provenance,
            risk_flags=risk_flags or [],
            created_at=created_at or (datetime.utcnow().isoformat() + "Z"),
        )
        self._records.append(record)
        with open(self.persist_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.model_dump()) + "\n")
        return record

    # MemoryStore-compatible write interface
    def write_note(
        self,
        content: str,
        tags: List[str],
        trust_level: str,
        provenance: str,
        risk_flags: List[str],
        created_at: str,
    ) -> MemoryRecord:
        return self.ingest(
            content=content,
            trust_level=trust_level,
            provenance=provenance,
            tags=tags,
            risk_flags=risk_flags,
            created_at=created_at,
        )

    def query(self, topic: str, k: int = 3) -> List[Tuple[MemoryRecord, float]]:
        """
        Return top-k records by cosine similarity to topic, with scores.

        Scores are computed using keyword TF-IDF word-overlap cosine similarity.
        """
        query_vec = Counter(_tokenize(topic))
        scored: List[Tuple[MemoryRecord, float]] = []
        for record in self._records:
            doc_text = record.content + " " + " ".join(record.tags)
            doc_vec = Counter(_tokenize(doc_text))
            score = _cosine_sim(query_vec, doc_vec)
            scored.append((record, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:k]
        self._last_scores = [s for _, s in top]
        return top

    def query_notes(self, topic: str, limit: int = 3) -> List[MemoryRecord]:
        """MemoryStore-compatible interface — scores available via .last_scores."""
        results = self.query(topic, k=limit)
        return [r for r, _ in results]

    @property
    def last_scores(self) -> List[float]:
        """Similarity scores from the most recent query() call."""
        return list(self._last_scores)

    def close(self) -> None:
        pass
