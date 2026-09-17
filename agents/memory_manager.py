from __future__ import annotations

from typing import Any

from chat.conversation_service import ConversationService


class AgentMemoryManager:
    """Adapter around existing conversation memory for multi-agent state."""

    def __init__(self, conversation_service: ConversationService) -> None:
        self._conversation_service = conversation_service

    def build_memory_snapshot(self) -> dict[str, Any]:
        state = self._conversation_service.state
        return {
            "conversation_history": [
                {"role": msg.role, "content": msg.content}
                for msg in state.conversation.messages[-20:]
            ],
            "conversation_summary": state.current_summary,
            "referenced_customers": list(state.referenced_customers),
            "referenced_orders": list(state.referenced_orders),
            "agent_outputs": list(state.agent_outputs[-15:]),
            "intermediate_results": list(state.intermediate_results[-20:]),
            "execution_plan": list(state.execution_plan),
            "previous_tool_calls": list(state.previous_tool_calls[-10:]),
        }

    def update_plan(self, plan: list[dict[str, Any]]) -> None:
        self._conversation_service.set_execution_plan(plan)

    def record_intermediate_result(self, source: str, payload: dict[str, Any]) -> None:
        self._conversation_service.add_intermediate_result(source, payload)

    def record_agent_output(self, payload: dict[str, Any]) -> None:
        self._conversation_service.add_agent_output(payload)

    def set_agent_status(self, agent: str, status: str) -> None:
        self._conversation_service.set_agent_status(agent, status)
