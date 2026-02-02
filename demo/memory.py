from __future__ import annotations

import json
import os
import sqlite3
from typing import List

from .schemas import MemoryRecord
from .utils import model_to_dict


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
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def write_note(
        self,
        content: str,
        tags: List[str],
        trust_level: str,
        provenance: str,
        risk_flags: List[str],
        created_at: str,
    ) -> MemoryRecord:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO memory (content, tags, trust_level, provenance, risk_flags, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                content,
                json.dumps(tags),
                trust_level,
                provenance,
                json.dumps(risk_flags),
                created_at,
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
        )

    def query_notes(self, topic: str, limit: int = 3) -> List[MemoryRecord]:
        cur = self.conn.cursor()
        if topic:
            like = f"%{topic}%"
            cur.execute(
                """
                SELECT * FROM memory
                WHERE content LIKE ? OR tags LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (like, like, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM memory
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=int(row["id"]),
            content=row["content"],
            tags=json.loads(row["tags"]),
            trust_level=row["trust_level"],
            provenance=row["provenance"],
            risk_flags=json.loads(row["risk_flags"]),
            created_at=row["created_at"],
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
