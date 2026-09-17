from __future__ import annotations

from time import perf_counter
from typing import Any

from agents.agent_context import AgentContext
from agents.agent_response import AgentResponse, AgentToolCall
from agents.base_agent import BaseAgent
from agents.prompts.order_prompt import ORDER_AGENT_PROMPT
from chat.openai_client import OpenAIClientWrapper
from chat.tool_executor import MCPToolExecutor


class OrderAgent(BaseAgent):
    """Specialist agent for order-only operations."""

    def __init__(self, *, openai_client: OpenAIClientWrapper, tool_executor: MCPToolExecutor) -> None:
        super().__init__(
            name="order_agent",
            description="Handles order retrieval, customer purchases, and order performance statistics.",
            capabilities=[
                "order retrieval",
                "order statistics",
                "highest order",
                "customer purchases",
                "order history",
            ],
            system_prompt=ORDER_AGENT_PROMPT,
            openai_client=openai_client,
            tool_executor=tool_executor,
            allowed_tools=[
                "list_orders",
                "get_order",
                "customer_orders",
                "create_order",
                "delete_order",
                "recent_orders",
                "highest_order",
                "calculate_customer_total",
            ],
        )

    def plan(self, context: AgentContext) -> list[dict[str, Any]]:
        entities = context.relevant_entities
        if entities.get("order_id"):
            return [{"tool": "get_order", "args": {"order_id": int(entities["order_id"])}}]
        if entities.get("customer_id"):
            customer_id = int(entities["customer_id"])
            return [
                {"tool": "customer_orders", "args": {"customer_id": customer_id}},
                {"tool": "calculate_customer_total", "args": {"customer_id": customer_id}},
            ]
        return [
            {"tool": "recent_orders", "args": {"days": 30}},
            {"tool": "highest_order", "args": {}},
        ]

    def reason(self, context: AgentContext) -> str:
        return (
            "Order-level data is required to determine transaction patterns, purchase history, "
            "and spending totals tied to customer or reporting requests."
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
            "agent_scope": "order",
            "request": context.user_request,
            "tool_outputs": payloads,
        }

        return self.return_result(
            objective=context.step.objective if context.step else "Order context retrieval",
            reasoning=reasoning,
            selected_tools=selected_tools,
            tool_calls=tool_calls,
            result=result,
            started_at=started_at,
        )
