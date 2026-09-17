from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExecutionPlanStep:
    """One planned execution step in the orchestration graph."""

    step_id: int
    title: str
    agent: str
    objective: str
    depends_on: list[int] = field(default_factory=list)
    can_run_in_parallel: bool = False


@dataclass(slots=True)
class AgentContext:
    """Scoped context passed into each agent execution."""

    user_request: str
    conversation_summary: str
    conversation_memory: dict[str, Any]
    relevant_entities: dict[str, Any]
    intent: dict[str, Any]
    previous_results: dict[str, Any]
    current_plan: list[ExecutionPlanStep]
    step: ExecutionPlanStep | None = None
