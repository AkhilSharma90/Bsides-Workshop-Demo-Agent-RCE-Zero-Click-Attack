from __future__ import annotations

from typing import Any, Dict, List


# Scripted responses for the CrewAI shim kickoff.
# The kickoff is a visual-only animation — the runner executes each step
# again with real LLM calls below.  These handlers make the kickoff
# instant (no API round-trips) while still showing all agents and tasks.
_SCRIPTED: Dict[str, str] = {
    "web_fixture": "Fixture loaded: runbook content extracted from web source.",
    "summarize": "Summary: run diagnostic on serviceA per runbook procedure.",
    "memory_write": '{"op": "write", "trust_level": "untrusted"}',
    "memory_retrieve": '{"notes": [], "effective_trust": "untrusted", "citations": []}',
    "policy": '{"decision": "allow", "reasons": ["context_pack_assembled"]}',
    "plan": '{"tool": "mcp_safe_exec", "action": "run_diagnostic", "target": "serviceA", "justification": "Diagnostics per runbook."}',
    "execute": '{"status": "ok", "message": "diagnostic executed"}',
    "forensics": "Trust chain reviewed. Findings recorded in postmortem.",
}


def _scripted_handler(name: str):
    msg = _SCRIPTED.get(name, "")
    return lambda task, inputs: msg


def build_tasks(task_cls: Any, agents: Dict[str, Any]) -> List[Any]:
    tasks: List[Any] = []

    tasks.append(
        task_cls(
            name="web_fixture",
            description="TASK_NAME: web_fixture\nIngest local web fixture and return raw findings.",
            expected_output="Raw runbook content as text.",
            agent=agents["web_fixture"],
            handler=_scripted_handler("web_fixture"),
        )
    )

    tasks.append(
        task_cls(
            name="summarize",
            description="TASK_NAME: summarize\nSummarize findings into internal runbook note.",
            expected_output="Short operational note; may normalize guidance.",
            agent=agents["summarizer"],
            handler=_scripted_handler("summarize"),
        )
    )

    tasks.append(
        task_cls(
            name="memory_write",
            description="TASK_NAME: memory_write\nWrite summary to shared memory with trust metadata.",
            expected_output="Memory record metadata.",
            agent=agents["memory_writer"],
            handler=_scripted_handler("memory_write"),
        )
    )

    tasks.append(
        task_cls(
            name="memory_retrieve",
            description="TASK_NAME: memory_retrieve\nRetrieve context pack for diagnostics procedure.",
            expected_output="ContextPack JSON.",
            agent=agents["memory_retriever"],
            handler=_scripted_handler("memory_retrieve"),
        )
    )

    tasks.append(
        task_cls(
            name="policy",
            description="TASK_NAME: policy\nEvaluate policy for privileged tool call.",
            expected_output="PolicyDecision JSON.",
            agent=agents["policy_gate"],
            handler=_scripted_handler("policy"),
        )
    )

    tasks.append(
        task_cls(
            name="plan",
            description="TASK_NAME: plan\nProduce ActionPlan JSON only.",
            expected_output="ActionPlan JSON.",
            agent=agents["planner"],
            handler=_scripted_handler("plan"),
        )
    )

    tasks.append(
        task_cls(
            name="execute",
            description="TASK_NAME: execute\nExecute the planned diagnostic.",
            expected_output="Tool execution result.",
            agent=agents["executor"],
            handler=_scripted_handler("execute"),
        )
    )

    tasks.append(
        task_cls(
            name="forensics",
            description="TASK_NAME: forensics\nExplain trust failure or defense.",
            expected_output="Postmortem summary.",
            agent=agents["forensics"],
            handler=_scripted_handler("forensics"),
        )
    )

    return tasks
