from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


TrustLevel = Literal["trusted", "untrusted"]
Decision = Literal["allow", "block", "require_verification"]


class MemoryRecord(BaseModel):
    id: int
    content: str
    tags: List[str]
    trust_level: TrustLevel
    provenance: str
    risk_flags: List[str] = Field(default_factory=list)
    created_at: str


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
