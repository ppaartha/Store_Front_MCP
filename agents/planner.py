from __future__ import annotations

from dataclasses import asdict

from agents.agent_context import AgentContext, ExecutionPlanStep
from agents.prompts.planner_prompt import PLANNER_PROMPT


class Planner:
    """Creates dependency-aware execution plans for specialist agents."""

    def __init__(self) -> None:
        self.prompt = PLANNER_PROMPT

    @staticmethod
    def _contains_any(text: str, terms: list[str]) -> bool:
        return any(term in text for term in terms)

    def generate_plan(self, context: AgentContext) -> list[ExecutionPlanStep]:
        text = context.user_request.lower()
        intent_text = str(context.intent.get("intent", "")).lower()
        combined = f"{text} {intent_text}"

        is_sales = self._contains_any(
            combined,
            ["sales", "revenue", "insight", "report", "trend", "analytics"],
        )
        is_order = self._contains_any(combined, ["order", "purchase", "highest order"])
        is_customer = self._contains_any(combined, ["customer", "client", "email", "country"])

        steps: list[ExecutionPlanStep] = []
        step_id = 1

        if is_customer or is_sales:
            steps.append(
                ExecutionPlanStep(
                    step_id=step_id,
                    title="Customer Context Retrieval",
                    agent="customer_agent",
                    objective="Retrieve customer references, segmentation hints, and base context.",
                )
            )
            step_id += 1

        if is_order or is_sales:
            depends = [1] if steps else []
            steps.append(
                ExecutionPlanStep(
                    step_id=step_id,
                    title="Order Context Retrieval",
                    agent="order_agent",
                    objective="Retrieve order-level activity, purchase patterns, and totals.",
                    depends_on=depends,
                    can_run_in_parallel=False,
                )
            )
            step_id += 1

        if is_sales:
            depends = [step.step_id for step in steps] or []
            steps.append(
                ExecutionPlanStep(
                    step_id=step_id,
                    title="Sales Insight Synthesis",
                    agent="analytics_agent",
                    objective="Generate revenue and sales insights from MCP analytics tools.",
                    depends_on=depends,
                    can_run_in_parallel=False,
                )
            )
            step_id += 1

        if not steps:
            steps.append(
                ExecutionPlanStep(
                    step_id=1,
                    title="General Customer-Order Context",
                    agent="customer_agent",
                    objective="Collect baseline customer context for general requests.",
                )
            )

        return steps

    @staticmethod
    def as_dict(plan: list[ExecutionPlanStep]) -> list[dict]:
        return [asdict(step) for step in plan]
