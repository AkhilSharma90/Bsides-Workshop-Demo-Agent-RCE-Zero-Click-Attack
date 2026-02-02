from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from .agents import build_agents
from .crewai_shim import Agent as ShimAgent
from .crewai_shim import Crew as ShimCrew
from .crewai_shim import Process as ShimProcess
from .crewai_shim import Task as ShimTask
from .llm import MultiProviderLLM
from .tasks import build_tasks


def _load_crewai() -> Tuple[Any, Any, Any, Any, bool]:
    use_shim = os.environ.get("DEMO_USE_SHIM", "") == "1"
    if use_shim:
        return ShimAgent, ShimTask, ShimCrew, ShimProcess, False
    try:
        from crewai import Agent, Crew, Process, Task  # type: ignore

        return Agent, Task, Crew, Process, True
    except Exception:
        return ShimAgent, ShimTask, ShimCrew, ShimProcess, False


def build_crew(
    mode: str,
    tools: Dict[str, Any],
    verbose: bool = False,
    pace_seconds: float = 0.0,
) -> Dict[str, Any]:
    AgentCls, TaskCls, CrewCls, ProcessCls, is_real = _load_crewai()

    llm = MultiProviderLLM.from_env()
    if is_real:
        tools = {}
    agents = build_agents(AgentCls, llm, tools, verbose=verbose)
    tasks = build_tasks(TaskCls, agents)

    crew_kwargs: Dict[str, Any] = dict(
        agents=list(agents.values()),
        tasks=tasks,
        process=ProcessCls.sequential,
        verbose=verbose,
    )
    if not is_real and pace_seconds > 0:
        crew_kwargs["pace_seconds"] = max(0.0, pace_seconds)
    crew = CrewCls(**crew_kwargs)

    return {
        "crew": crew,
        "agents": agents,
        "tasks": tasks,
        "llm": llm,
        "is_real": is_real,
    }
