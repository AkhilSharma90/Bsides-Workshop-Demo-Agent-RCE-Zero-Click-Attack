from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Dict


class ReplayStore:
    """JSONL-backed cache for LLM prompt/response pairs.

    Used by the offline demo mode so the talk never fails due to
    API timeouts, rate limits, or missing WiFi.

    File format: one JSON object per line, each with keys:
        key      — 16-char hex (sha256 of prompt)
        response — full LLM response string
        ts       — ISO-8601 UTC timestamp when recorded
    """

    def __init__(self, path: str) -> None:
        self.path = os.path.abspath(path)
        self._cache: Dict[str, str] = {}
        self.load_all()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _prompt_key(self, prompt: str) -> str:
        """Return 16-char hex digest of the stripped prompt."""
        return hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest()[:16]

    def has(self, key: str) -> bool:
        """Return True if this key exists in the loaded cache."""
        return key in self._cache

    def get(self, key: str) -> str:
        """Return cached response.  Raises KeyError if not found."""
        return self._cache[key]

    def record(self, key: str, response: str) -> None:
        """Persist a new key→response pair to the JSONL file."""
        self._cache[key] = response
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        entry = {
            "key": key,
            "response": response,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def load_all(self) -> None:
        """Read the JSONL file into the in-memory dict.

        Creates an empty file if the path doesn't exist yet.
        Silently skips malformed lines.
        """
        self._cache = {}
        if not os.path.exists(self.path):
            # Touch the file so future record() calls can append
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "a", encoding="utf-8"):
                pass
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    key = entry.get("key", "")
                    response = entry.get("response", "")
                    if key:
                        self._cache[key] = response
                except json.JSONDecodeError:
                    continue

    def __len__(self) -> int:
        return len(self._cache)

    def __repr__(self) -> str:
        return f"ReplayStore(path={self.path!r}, entries={len(self._cache)})"
