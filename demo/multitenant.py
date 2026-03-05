"""
TenantAwareMemoryStore

Wraps MemoryStore to demonstrate cross-tenant memory bleed.

Vulnerability: in vulnerable mode, tenant_id is ignored during queries, so
one tenant's data is visible to another tenant's agent.

Defense: in defended mode, queries are filtered strictly by tenant_id.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from .memory import MemoryStore
from .schemas import MemoryRecord


class TenantAwareMemoryStore(MemoryStore):
    """
    Memory store with tenant isolation (or deliberate lack thereof).

    Demo flow:
    - Tenant A writes a poisoned note (tenant_id="tenant_a")
    - Tenant B queries memory (tenant_id="tenant_b")
    - Vulnerable mode: Tenant B retrieves Tenant A's note (no isolation)
    - Defended mode: Tenant B retrieves nothing (strict tenant filter)
    """

    def __init__(self, db_path: str, mode: str = "vulnerable") -> None:
        self.multi_tenant_mode = mode
        # Call grandparent __init__ directly to avoid double _init_schema
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
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
        self.conn.commit()

    def write_note(
        self,
        content: str,
        tags: List[str],
        trust_level: str,
        provenance: str,
        risk_flags: List[str],
        created_at: str,
        tenant_id: Optional[str] = None,
    ) -> MemoryRecord:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO memory (content, tags, trust_level, provenance, risk_flags, created_at, tenant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content,
                json.dumps(tags),
                trust_level,
                provenance,
                json.dumps(risk_flags),
                created_at,
                tenant_id,
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
            tenant_id=tenant_id,
        )

    def query_notes(self, topic: str, limit: int = 3, tenant_id: Optional[str] = None) -> List[MemoryRecord]:  # type: ignore[override]
        if self.multi_tenant_mode == "defended" and tenant_id is not None:
            # Defended: strictly isolate by tenant — Tenant B cannot see Tenant A's data
            return self._query_by_tenant(topic, limit, tenant_id)
        # Vulnerable: ignore tenant_id entirely — shared index (memory bleed)
        return super().query_notes(topic, limit)

    def _query_by_tenant(self, topic: str, limit: int, tenant_id: str) -> List[MemoryRecord]:
        cur = self.conn.cursor()
        if topic:
            like = f"%{topic}%"
            cur.execute(
                """
                SELECT * FROM memory
                WHERE (content LIKE ? OR tags LIKE ?) AND tenant_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (like, like, tenant_id, limit),
            )
        else:
            cur.execute(
                """
                SELECT * FROM memory
                WHERE tenant_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (tenant_id, limit),
            )
        rows = cur.fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        col_names = row.keys()
        return MemoryRecord(
            id=int(row["id"]),
            content=row["content"],
            tags=json.loads(row["tags"]),
            trust_level=row["trust_level"],
            provenance=row["provenance"],
            risk_flags=json.loads(row["risk_flags"]),
            created_at=row["created_at"],
            tenant_id=row["tenant_id"] if "tenant_id" in col_names else None,
        )
