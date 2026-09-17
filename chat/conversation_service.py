"""Conversation memory service for long-running educational chat sessions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from chat.conversation import Conversation


@dataclass(slots=True)
class TurnMetrics:
    """Execution telemetry captured per user turn for analytics panels."""

    total_time_ms: float = 0.0
    tool_count: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(slots=True)
class ConversationState:
    """Extended memory for a single Streamlit session."""

    conversation: Conversation = field(default_factory=Conversation)
    current_summary: str = ""
    previous_summary: str = ""
    summary_updates: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    known_entities: dict[str, Any] = field(default_factory=dict)
    conversation_state: str = "open"
    previous_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    referenced_customers: list[Any] = field(default_factory=list)
    referenced_orders: list[Any] = field(default_factory=list)
    intent_counts: dict[str, int] = field(default_factory=dict)
    tool_usage: dict[str, int] = field(default_factory=dict)
    turn_count: int = 0
    metrics_history: list[TurnMetrics] = field(default_factory=list)
    execution_plan: list[dict[str, Any]] = field(default_factory=list)
    agent_outputs: list[dict[str, Any]] = field(default_factory=list)
    intermediate_results: list[dict[str, Any]] = field(default_factory=list)
    collaboration_messages: list[dict[str, Any]] = field(default_factory=list)
    agent_status: dict[str, str] = field(default_factory=dict)
    agent_usage: dict[str, int] = field(default_factory=dict)
    planning_durations_ms: list[float] = field(default_factory=list)
    debug_events: list[dict[str, Any]] = field(default_factory=list)


class ConversationService:
    """Manages session memory and aggregate analytics for the AI assistant."""

    def __init__(self, state: ConversationState) -> None:
        self._state = state

    @property
    def state(self) -> ConversationState:
        return self._state

    def clear(self) -> None:
        self._state.conversation.clear()
        self._state.current_summary = ""
        self._state.previous_summary = ""
        self._state.summary_updates.clear()
        self._state.pending_tasks.clear()
        self._state.known_entities.clear()
        self._state.conversation_state = "open"
        self._state.previous_tool_calls.clear()
        self._state.referenced_customers.clear()
        self._state.referenced_orders.clear()
        self._state.intent_counts.clear()
        self._state.tool_usage.clear()
        self._state.turn_count = 0
        self._state.metrics_history.clear()
        self._state.execution_plan.clear()
        self._state.agent_outputs.clear()
        self._state.intermediate_results.clear()
        self._state.collaboration_messages.clear()
        self._state.agent_status.clear()
        self._state.agent_usage.clear()
        self._state.planning_durations_ms.clear()
        self._state.debug_events.clear()

    def token_estimate(self) -> int:
        # Lightweight estimate for UI: ~1 token per 4 characters.
        char_count = sum(len(m.content) for m in self._state.conversation.messages)
        return max(1, char_count // 4)

    def register_intent(self, intent: str) -> None:
        self._state.intent_counts[intent] = self._state.intent_counts.get(intent, 0) + 1

    def register_tool_usage(self, tool_name: str) -> None:
        self._state.tool_usage[tool_name] = self._state.tool_usage.get(tool_name, 0) + 1

    def add_tool_call(self, call: dict[str, Any]) -> None:
        self._state.previous_tool_calls.append(call)
        self._state.previous_tool_calls = self._state.previous_tool_calls[-30:]

    def set_execution_plan(self, plan: list[dict[str, Any]]) -> None:
        self._state.execution_plan = plan

    def add_intermediate_result(self, source: str, payload: dict[str, Any]) -> None:
        self._state.intermediate_results.append({"source": source, **payload})
        self._state.intermediate_results = self._state.intermediate_results[-50:]

    def add_agent_output(self, payload: dict[str, Any]) -> None:
        agent = str(payload.get("agent", "unknown_agent"))
        self._state.agent_outputs.append(payload)
        self._state.agent_outputs = self._state.agent_outputs[-40:]
        self._state.agent_usage[agent] = self._state.agent_usage.get(agent, 0) + 1
        self._state.agent_status[agent] = str(payload.get("status", "completed"))

    def add_collaboration_messages(self, messages: list[dict[str, Any]]) -> None:
        self._state.collaboration_messages.extend(messages)
        self._state.collaboration_messages = self._state.collaboration_messages[-60:]

    def set_agent_status(self, agent: str, status: str) -> None:
        self._state.agent_status[agent] = status

    def add_planning_duration(self, duration_ms: float) -> None:
        self._state.planning_durations_ms.append(duration_ms)
        self._state.planning_durations_ms = self._state.planning_durations_ms[-100:]

    def log_event(self, event_type: str, message: str, payload: dict[str, Any] | None = None) -> None:
        self._state.debug_events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "message": message,
                "payload": payload or {},
            }
        )
        self._state.debug_events = self._state.debug_events[-500:]

    def update_references(self, entities: dict[str, Any]) -> None:
        customer_id = entities.get("customer_id")
        order_id = entities.get("order_id")
        if customer_id and customer_id not in self._state.referenced_customers:
            self._state.referenced_customers.append(customer_id)
            self._state.referenced_customers = self._state.referenced_customers[-20:]
        if order_id and order_id not in self._state.referenced_orders:
            self._state.referenced_orders.append(order_id)
            self._state.referenced_orders = self._state.referenced_orders[-20:]

    def update_summary(self, *, new_summary: str, known_entities: dict[str, Any], pending_tasks: list[str], state: str) -> None:
        if self._state.current_summary and self._state.current_summary != new_summary:
            self._state.previous_summary = self._state.current_summary
            self._state.summary_updates.append(new_summary)
            self._state.summary_updates = self._state.summary_updates[-10:]
        self._state.current_summary = new_summary
        self._state.known_entities.update({k: v for k, v in known_entities.items() if v not in (None, "")})
        self._state.pending_tasks = pending_tasks
        self._state.conversation_state = state

    def start_timer(self) -> float:
        return perf_counter()

    def finish_turn(self, *, started_at: float, tool_count: int, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        elapsed_ms = (perf_counter() - started_at) * 1000
        self._state.turn_count += 1
        self._state.metrics_history.append(
            TurnMetrics(
                total_time_ms=elapsed_ms,
                tool_count=tool_count,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
        )
        self._state.metrics_history = self._state.metrics_history[-100:]

    def analytics_snapshot(self) -> dict[str, Any]:
        metrics = self._state.metrics_history
        avg_ms = (sum(m.total_time_ms for m in metrics) / len(metrics)) if metrics else 0.0
        avg_planning_ms = (
            sum(self._state.planning_durations_ms) / len(self._state.planning_durations_ms)
            if self._state.planning_durations_ms
            else 0.0
        )
        total_prompt = sum(m.prompt_tokens for m in metrics)
        total_completion = sum(m.completion_tokens for m in metrics)
        total_tokens = sum(m.total_tokens for m in metrics)
        most_used_agent = ""
        if self._state.agent_usage:
            most_used_agent = max(self._state.agent_usage.items(), key=lambda item: item[1])[0]

        most_used_tool = ""
        if self._state.tool_usage:
            most_used_tool = max(self._state.tool_usage.items(), key=lambda item: item[1])[0]

        return {
            "conversation_count": self._state.turn_count,
            "average_response_time_ms": round(avg_ms, 2),
            "average_planning_time_ms": round(avg_planning_ms, 2),
            "tool_usage_frequency": dict(sorted(self._state.tool_usage.items(), key=lambda x: x[1], reverse=True)),
            "agent_usage_frequency": dict(sorted(self._state.agent_usage.items(), key=lambda x: x[1], reverse=True)),
            "intent_distribution": dict(sorted(self._state.intent_counts.items(), key=lambda x: x[1], reverse=True)),
            "most_used_agent": most_used_agent,
            "most_used_tool": most_used_tool,
            "agent_status": dict(self._state.agent_status),
            "agent_outputs": list(self._state.agent_outputs[-10:]),
            "execution_plan": list(self._state.execution_plan),
            "collaboration_messages": list(self._state.collaboration_messages[-30:]),
            "debug_events": list(self._state.debug_events[-100:]),
            "token_usage": {
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "total_tokens": total_tokens,
            },
        }
