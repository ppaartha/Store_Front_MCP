from __future__ import annotations

from abc import ABC, abstractmethod
from time import perf_counter
from typing import Any

from agents.agent_context import AgentContext
from agents.agent_response import AgentResponse, AgentToolCall
from chat.openai_client import OpenAIClientWrapper
from chat.tool_executor import MCPToolExecutor


class BaseAgent(ABC):
    """Abstract base class for all specialized MCP-driven agents."""

    def __init__(
        self,
        *,
        name: str,
        description: str,
        capabilities: list[str],
        system_prompt: str,
        openai_client: OpenAIClientWrapper,
        tool_executor: MCPToolExecutor,
        allowed_tools: list[str],
    ) -> None:
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.system_prompt = system_prompt
        self._openai_client = openai_client
        self._tool_executor = tool_executor
        self._allowed_tools = set(allowed_tools)

    @abstractmethod
    def plan(self, context: AgentContext) -> list[dict[str, Any]]:
        """Create the execution sub-plan for this agent."""

    @abstractmethod
    def reason(self, context: AgentContext) -> str:
        """Explain why this agent is needed for the current request."""

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResponse:
        """Run MCP tools and return a structured agent response."""

    def use_tool(self, tool_name: str, arguments: dict[str, Any]) -> AgentToolCall:
        if tool_name not in self._allowed_tools:
            return AgentToolCall(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                duration_ms=0.0,
                response=None,
                error=f"Tool '{tool_name}' not allowed for {self.name}.",
            )

        record = self._tool_executor.execute_tool(tool_name, arguments)
        return AgentToolCall(
            tool_name=record.tool_name,
            arguments=record.arguments,
            success=record.success,
            duration_ms=record.duration_ms,
            response=record.response,
            error=record.error,
        )

    def return_result(
        self,
        *,
        objective: str,
        reasoning: str,
        selected_tools: list[str],
        tool_calls: list[AgentToolCall],
        result: dict[str, Any],
        started_at: float,
    ) -> AgentResponse:
        completed_at = perf_counter() * 1000
        return AgentResponse(
            agent_name=self.name,
            status="completed",
            objective=objective,
            reasoning=reasoning,
            selected_tools=selected_tools,
            tool_calls=tool_calls,
            result=result,
            started_at_ms=started_at,
            completed_at_ms=completed_at,
        )
