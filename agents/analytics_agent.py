from __future__ import annotations

from time import perf_counter
from typing import Any

from agents.agent_context import AgentContext
from agents.agent_response import AgentResponse, AgentToolCall
from agents.base_agent import BaseAgent
from agents.prompts.analytics_prompt import ANALYTICS_AGENT_PROMPT
from chat.openai_client import OpenAIClientWrapper
from chat.tool_executor import MCPToolExecutor


class AnalyticsAgent(BaseAgent):
    """Specialist agent for analytics and sales insight synthesis."""

    def __init__(self, *, openai_client: OpenAIClientWrapper, tool_executor: MCPToolExecutor) -> None:
        super().__init__(
            name="analytics_agent",
            description="Builds revenue trends, business insights, and executive summaries from MCP outputs.",
            capabilities=[
                "revenue analysis",
                "country analysis",
                "customer segmentation",
                "monthly reports",
                "sales trends",
                "executive summaries",
            ],
            system_prompt=ANALYTICS_AGENT_PROMPT,
            openai_client=openai_client,
            tool_executor=tool_executor,
            allowed_tools=[
                "generate_sales_insights",
                "sales_summary",
                "list_sales",
                "recent_orders",
                "list_orders",
                "list_customers",
            ],
        )

    def plan(self, context: AgentContext) -> list[dict[str, Any]]:
        text = context.user_request.lower()
        if "trend" in text or "monthly" in text or "insight" in text or "sales" in text or "revenue" in text:
            return [
                {"tool": "generate_sales_insights", "args": {}},
                {"tool": "sales_summary", "args": {}},
            ]
        return [{"tool": "sales_summary", "args": {}}]

    def reason(self, context: AgentContext) -> str:
        return (
            "The request requires KPI synthesis and business interpretation; the analytics agent "
            "uses sales MCP tools to produce data-backed summaries and trends."
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
            if call.success and tool_name == "generate_sales_insights":
                break

        result = {
            "agent_scope": "analytics",
            "request": context.user_request,
            "tool_outputs": payloads,
        }

        return self.return_result(
            objective=context.step.objective if context.step else "Sales insight synthesis",
            reasoning=reasoning,
            selected_tools=selected_tools,
            tool_calls=tool_calls,
            result=result,
            started_at=started_at,
        )
