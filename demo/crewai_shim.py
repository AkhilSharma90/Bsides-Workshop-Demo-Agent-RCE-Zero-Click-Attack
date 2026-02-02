from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Dict, List, Optional


class Process(Enum):
    sequential = "sequential"


@dataclass
class Agent:
    role: str
    goal: str
    backstory: str = ""
    llm: Any = None
    tools: List[Any] = field(default_factory=list)
    verbose: bool = False
    allow_delegation: bool = False

    def run(self, prompt: str, **kwargs: Any) -> str:
        if self.llm is None:
            return ""
        if hasattr(self.llm, "complete"):
            return self.llm.complete(prompt, agent=self, **kwargs)
        if callable(self.llm):
            return self.llm(prompt)
        return ""


@dataclass
class Task:
    description: str
    expected_output: str
    agent: Agent
    context: Optional[List["Task"]] = None
    name: Optional[str] = None
    output: Optional[str] = None
    handler: Optional[Callable[["Task", Dict[str, Any]], str]] = None


@dataclass
class Crew:
    agents: List[Agent]
    tasks: List[Task]
    process: Process = Process.sequential
    verbose: bool = False
    pace_seconds: float = 0.0
    max_log_chars: int = 1200

    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> str:
        inputs = inputs or {}
        last_output = ""
        seen_agents: set[str] = set()
        if self.verbose:
            print(f"[CrewAI shim] Kickoff with {len(self.tasks)} tasks")
            self._maybe_pause()
        for idx, task in enumerate(self.tasks, start=1):
            if self.verbose:
                task_name = task.name or "unnamed"
                print(f"[CrewAI shim] Task {idx}/{len(self.tasks)}: {task_name} ({task.agent.role})")
                self._maybe_pause()
                agent_key = task.agent.role or f"agent_{idx}"
                if agent_key not in seen_agents:
                    for line in self._agent_detail_lines(task.agent):
                        print(line)
                        self._maybe_pause()
                    seen_agents.add(agent_key)
            context_outputs = []
            if task.context:
                context_outputs = [t.output for t in task.context if t.output]
            prompt = self._build_prompt(task, context_outputs, inputs)
            if self.verbose:
                print("[CrewAI shim] Prompt:")
                print(self._truncate(prompt))
                self._maybe_pause()
            if task.handler:
                task.output = task.handler(task, inputs)
            else:
                task.output = task.agent.run(prompt, inputs=inputs)
            last_output = task.output
            if self.verbose:
                print("[CrewAI shim] Output:")
                print(self._truncate(task.output or ""))
                self._maybe_pause()
                print(f"[CrewAI shim] Task complete: {task.name or 'unnamed'}")
                self._maybe_pause()
        return last_output

    @staticmethod
    def _build_prompt(task: Task, context_outputs: List[str], inputs: Dict[str, Any]) -> str:
        parts = [
            f"TASK_NAME: {task.name or 'unnamed'}",
            f"ROLE: {task.agent.role}",
            f"GOAL: {task.agent.goal}",
            "DESCRIPTION:",
            task.description,
            "EXPECTED_OUTPUT:",
            task.expected_output,
        ]
        if context_outputs:
            parts.append("CONTEXT:")
            parts.extend(context_outputs)
        if inputs:
            parts.append("INPUTS:")
            parts.append(str(inputs))
        return "\n".join(parts)

    @staticmethod
    def _tool_label(tool: Any) -> str:
        if tool is None:
            return "unknown"
        name = getattr(tool, "name", None)
        if isinstance(name, str) and name:
            return name
        func_name = getattr(tool, "__name__", None)
        if isinstance(func_name, str) and func_name:
            return func_name
        cls = getattr(tool, "__class__", None)
        if cls is not None:
            class_name = getattr(cls, "__name__", None)
            if isinstance(class_name, str) and class_name:
                return class_name
        return str(tool)

    def _agent_detail_lines(self, agent: Agent) -> List[str]:
        role = agent.role or "unknown"
        goal = self._truncate(agent.goal or "")
        backstory = self._truncate(agent.backstory or "")
        tools = [self._tool_label(tool) for tool in (agent.tools or [])]
        tools_text = ", ".join(tools) if tools else "none"
        lines = [
            f"[CrewAI shim] Agent role: {role}",
            f"[CrewAI shim] Goal: {goal}",
        ]
        if backstory:
            lines.append(f"[CrewAI shim] Backstory: {backstory}")
        lines.append(f"[CrewAI shim] Tools: {tools_text}")
        lines.append(f"[CrewAI shim] Allow delegation: {agent.allow_delegation}")
        return lines

    def _maybe_pause(self) -> None:
        if self.pace_seconds > 0:
            time.sleep(self.pace_seconds)

    def _truncate(self, text: str) -> str:
        if len(text) > self.max_log_chars:
            return text[: self.max_log_chars] + "... (truncated)"
        return text
