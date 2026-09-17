from __future__ import annotations

from time import perf_counter
from typing import Any

from agents.agent_context import AgentContext
from agents.agent_response import AgentResponse, AgentToolCall
from agents.base_agent import BaseAgent
from agents.prompts.customer_prompt import CUSTOMER_AGENT_PROMPT
from chat.openai_client import OpenAIClientWrapper
from chat.tool_executor import MCPToolExecutor


class CustomerAgent(BaseAgent):
    """Specialist agent for customer-only operations."""

    def __init__(self, *, openai_client: OpenAIClientWrapper, tool_executor: MCPToolExecutor) -> None:
        super().__init__(
            name="customer_agent",
            description="Handles customer lookup, profile retrieval, and customer segmentation context.",
            capabilities=[
                "customer lookup",
                "customer search",
                "customer statistics",
                "customer summaries",
            ],
            system_prompt=CUSTOMER_AGENT_PROMPT,
            openai_client=openai_client,
            tool_executor=tool_executor,
            allowed_tools=[
                "search_customer",
                "get_customer",
                "create_customer",
                "update_customer",
                "delete_customer",
                "list_customers",
                "customers_by_country",
                "customers_by_status",
                "count_customers",
                "search_customer_email",
            ],
        )

    def plan(self, context: AgentContext) -> list[dict[str, Any]]:
        entities = context.relevant_entities
        if entities.get("email"):
            return [{"tool": "search_customer_email", "args": {"email": entities["email"]}}]
        if entities.get("country"):
            return [{"tool": "customers_by_country", "args": {"country": entities["country"]}}]
        if entities.get("customer_id"):
            return [{"tool": "get_customer", "args": {"customer_id": int(entities["customer_id"])}}]
        return [
            {"tool": "count_customers", "args": {}},
            {"tool": "list_customers", "args": {}},
        ]

    def reason(self, context: AgentContext) -> str:
        return (
            "Customer information is required to ground user intent, extract relevant segments, "
            "and provide accurate customer-level context for downstream agents."
        )

    def execute(self, context: AgentContext) -> AgentResponse:
        started_at = perf_counter() * 1000
        reasoning = self.reason(context)
        tool_plan = self.plan(context)

        tool_calls: list[AgentToolCall] = []
        selected_tools: list[str] = []
        payloads: list[dict[str, Any]] = []

        for item in tool_plan:
            tool_name = str(item["tool"])
            args = dict(item.get("args", {}))
            selected_tools.append(tool_name)
            call = self.use_tool(tool_name, args)
            tool_calls.append(call)
            payloads.append(
                {
                    "tool": call.tool_name,
                    "success": call.success,
                    "error": call.error,
                    "response": call.response,
                    "duration_ms": round(call.duration_ms, 2),
                }
            )

        result = {
            "agent_scope": "customer",
            "request": context.user_request,
            "tool_outputs": payloads,
        }

        return self.return_result(
            objective=context.step.objective if context.step else "Customer context retrieval",
            reasoning=reasoning,
            selected_tools=selected_tools,
            tool_calls=tool_calls,
            result=result,
            started_at=started_at,
        )
