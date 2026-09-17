from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentToolCall:
    """Execution metadata for one MCP tool call."""

    tool_name: str
    arguments: dict[str, Any]
    success: bool
    duration_ms: float
    response: Any
    error: str | None = None


@dataclass(slots=True)
class AgentResponse:
    """Structured output produced by one specialized agent."""

    agent_name: str
    status: str
    objective: str
    reasoning: str
    selected_tools: list[str] = field(default_factory=list)
    tool_calls: list[AgentToolCall] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    started_at_ms: float = 0.0
    completed_at_ms: float = 0.0

    @property
    def execution_time_ms(self) -> float:
        return max(0.0, self.completed_at_ms - self.started_at_ms)
