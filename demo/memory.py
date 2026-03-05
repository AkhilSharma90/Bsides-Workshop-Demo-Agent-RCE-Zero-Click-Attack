from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from typing import List

from .schemas import MemoryRecord
from .utils import model_to_dict


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


class MemoryStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tags TEXT NOT NULL,
                trust_level TEXT NOT NULL,
                provenance TEXT NOT NULL,
                risk_flags TEXT NOT NULL,
                created_at TEXT NOT NULL,
                taint_chain TEXT NOT NULL DEFAULT '[]',
                content_hash TEXT NOT NULL DEFAULT '',
                quarantined INTEGER NOT NULL DEFAULT 0,
                tenant_id TEXT
            )
            """
        )
        # Migrate existing databases that lack the new columns
        existing = {row[1] for row in cur.execute("PRAGMA table_info(memory)").fetchall()}
        for col, ddl in [
            ("taint_chain", "TEXT NOT NULL DEFAULT '[]'"),
            ("content_hash", "TEXT NOT NULL DEFAULT ''"),
            ("quarantined", "INTEGER NOT NULL DEFAULT 0"),
            ("tenant_id", "TEXT"),
        ]:
            if col not in existing:
                cur.execute(f"ALTER TABLE memory ADD COLUMN {col} {ddl}")
        self.conn.commit()

    def write_note(
        self,
        content: str,
        tags: List[str],
        trust_level: str,
        provenance: str,
        risk_flags: List[str],
        created_at: str,
        taint_chain: List[str] | None = None,
    ) -> MemoryRecord:
        ch = _content_hash(content)
        tc = taint_chain or []
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO memory (content, tags, trust_level, provenance, risk_flags, created_at, taint_chain, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content,
                json.dumps(tags),
                trust_level,
                provenance,
                json.dumps(risk_flags),
                created_at,
                json.dumps(tc),
                ch,
            ),
        )
        self.conn.commit()
        record_id = cur.lastrowid
        return MemoryRecord(
            id=record_id,
            content=content,
            tags=tags,
            trust_level=trust_level,
            provenance=provenance,
            risk_flags=risk_flags,
            created_at=created_at,
            taint_chain=tc,
            content_hash=ch,
        )

    def query_notes(self, topic: str, limit: int = 3) -> List[MemoryRecord]:
        cur = self.conn.cursor()
        if topic:
            like = f"%{topic}%"
            cur.execute(
                """
                SELECT * FROM memory
                WHERE (content LIKE ? OR tags LIKE ?) AND quarantined = 0
                ORDER BY id DESC
                LIMIT ?
                """,
                (like, like, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM memory
                WHERE quarantined = 0
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def quarantine_note(self, record_id: int) -> None:
        """Mark a memory record as quarantined — it will not appear in future queries."""
        cur = self.conn.cursor()
        cur.execute("UPDATE memory SET quarantined = 1 WHERE id = ?", (record_id,))
        self.conn.commit()

    def query_quarantine(self) -> List[MemoryRecord]:
        """Return all quarantined records (for forensic review)."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM memory WHERE quarantined = 1 ORDER BY id")
        return [self._row_to_record(row) for row in cur.fetchall()]

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        cols = row.keys()
        return MemoryRecord(
            id=int(row["id"]),
            content=row["content"],
            tags=json.loads(row["tags"]),
            trust_level=row["trust_level"],
            provenance=row["provenance"],
            risk_flags=json.loads(row["risk_flags"]),
            created_at=row["created_at"],
            taint_chain=json.loads(row["taint_chain"]) if "taint_chain" in cols else [],
            content_hash=row["content_hash"] if "content_hash" in cols else "",
            quarantined=bool(row["quarantined"]) if "quarantined" in cols else False,
            tenant_id=row["tenant_id"] if "tenant_id" in cols else None,
        )

    def close(self) -> None:
        self.conn.close()


class JsonlMemoryStore:
    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("")

    def write_note(
        self,
        content: str,
        tags: List[str],
        trust_level: str,
        provenance: str,
        risk_flags: List[str],
        created_at: str,
        taint_chain: List[str] | None = None,
    ) -> MemoryRecord:
        records = self._read_all()
        record_id = len(records) + 1
        record = MemoryRecord(
            id=record_id,
            content=content,
            tags=tags,
            trust_level=trust_level,
            provenance=provenance,
            risk_flags=risk_flags,
            created_at=created_at,
            taint_chain=taint_chain or [],
        )
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(model_to_dict(record), ensure_ascii=True) + "\n")
        return record

    def query_notes(self, topic: str, limit: int = 3) -> List[MemoryRecord]:
        records = self._read_all()
        if topic:
            lowered = topic.lower()
            records = [
                r
                for r in records
                if lowered in r.content.lower()
                or lowered in " ".join(r.tags).lower()
            ]
        return list(reversed(records))[:limit]

    def _read_all(self) -> List[MemoryRecord]:
        records: List[MemoryRecord] = []
        with open(self.path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                records.append(MemoryRecord(**data))
        return records

    def close(self) -> None:
        return None
