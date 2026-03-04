from __future__ import annotations

import datetime
import hashlib
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


TrustLevel = Literal["trusted", "untrusted"]
Decision = Literal["allow", "block", "require_verification"]


class AllowedTarget(str, Enum):
    serviceA = "serviceA"
    serviceB = "serviceB"


class MemoryRecord(BaseModel):
    id: int
    content: str
    tags: List[str]
    trust_level: TrustLevel
    provenance: str
    risk_flags: List[str] = Field(default_factory=list)
    created_at: str
    tenant_id: Optional[str] = None
    taint_chain: List[str] = Field(default_factory=list)
    content_hash: str = ""
    quarantined: bool = False


class ContextPack(BaseModel):
    notes: List[MemoryRecord]
    effective_trust: TrustLevel
    citations: List[str]


class PolicyDecision(BaseModel):
    decision: Decision
    reasons: List[str]
    enforced: bool = True


class ActionPlan(BaseModel):
    tool: Literal["mcp_safe_exec"]
    action: Literal["run_diagnostic"]
    target: str
    justification: str
    source_memory_ids: List[int]
    taint_chain: List[str] = Field(default_factory=list)


class StrictActionPlan(BaseModel):
    """Stricter version of ActionPlan — target must be in the AllowedTarget enum.
    Rejects anything not in the allowlist at parse time (Pydantic validation error)."""
    tool: Literal["mcp_safe_exec"]
    action: Literal["run_diagnostic"]
    target: AllowedTarget
    target_params: Optional[str] = None
    justification: str
    source_memory_ids: List[int]
    taint_chain: List[str] = Field(default_factory=list)


class CapabilityToken(BaseModel):
    token: str
    issued_at: str
    valid_for_target: str
    expires_at: str
    signed_by: str

    def is_valid(self, target: str) -> bool:
        if target != self.valid_for_target:
            return False
        try:
            expiry = datetime.datetime.fromisoformat(self.expires_at.rstrip("Z"))
            now = datetime.datetime.utcnow()
            return now < expiry
        except Exception:
            return False

    @classmethod
    def issue(cls, target: str, decision_id: str, ttl_seconds: int = 30) -> "CapabilityToken":
        secret = "bsides_demo_secret"
        raw = f"{decision_id}:{target}:{secret}"
        token_hex = hashlib.sha256(raw.encode()).hexdigest()[:16]
        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(seconds=ttl_seconds)
        return cls(
            token=token_hex,
            issued_at=now.isoformat() + "Z",
            valid_for_target=target,
            expires_at=expires.isoformat() + "Z",
            signed_by="PolicyGateAgent",
        )


class MCPPayload(BaseModel):
    action: Literal["run_diagnostic"]
    target: str


class MCPResponse(BaseModel):
    status: Literal["ok", "rejected"]
    message: str
    artifacts_written: List[str] = Field(default_factory=list)


class TraceEvent(BaseModel):
    ts: str
    agent_name: str
    task_name: str
    inputs: dict
    outputs: dict
    memory_ops: List[dict] = Field(default_factory=list)
    tool_calls: List[dict] = Field(default_factory=list)
    obfuscation_method: Optional[str] = None
    atlas_tags: List[str] = Field(default_factory=list)
    taint_chain: List[str] = Field(default_factory=list)
