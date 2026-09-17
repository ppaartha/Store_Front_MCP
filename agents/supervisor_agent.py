from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from typing import Any

from agents.agent_context import AgentContext
from agents.agent_registry import AgentRegistry
from agents.agent_response import AgentResponse
from agents.memory_manager import AgentMemoryManager
from agents.planner import Planner
from agents.prompts.supervisor_prompt import SUPERVISOR_PROMPT


class SupervisorAgent:
    """Coordinates planning, delegation, and final result assembly."""

    def __init__(
        self,
        *,
        planner: Planner,
        registry: AgentRegistry,
        memory_manager: AgentMemoryManager,
    ) -> None:
        self.name = "supervisor_agent"
        self.description = "Coordinates specialist agents and composes final response context."
        self.capabilities = [
            "goal understanding",
            "task planning",
            "agent delegation",
            "result synthesis",
        ]
        self.system_prompt = SUPERVISOR_PROMPT
        self._planner = planner
        self._registry = registry
        self._memory = memory_manager

    def execute(self, context: AgentContext) -> dict[str, Any]:
        started_at = perf_counter() * 1000
        plan = self._planner.generate_plan(context)
        plan_payload = self._planner.as_dict(plan)
        self._memory.update_plan(plan_payload)

        agent_outputs: list[AgentResponse] = []
        collaboration_messages: list[dict[str, Any]] = []
        previous_results: dict[str, Any] = dict(context.previous_results)

        for step in plan:
            agent = self._registry.get(step.agent)
            if agent is None:
                collaboration_messages.append(
                    {
                        "from": self.name,
                        "to": step.agent,
                        "message": f"Skipped step {step.step_id}; agent not registered.",
                    }
                )
                continue

            self._memory.set_agent_status(agent.name, "running")

            scoped_context = AgentContext(
                user_request=context.user_request,
                conversation_summary=context.conversation_summary,
                conversation_memory=context.conversation_memory,
                relevant_entities=context.relevant_entities,
                intent=context.intent,
                previous_results=previous_results,
                current_plan=plan,
                step=step,
            )
            collaboration_messages.append(
                {
                    "from": self.name,
                    "to": agent.name,
                    "message": f"Execute step {step.step_id}: {step.objective}",
                }
            )

            response = agent.execute(scoped_context)
            agent_outputs.append(response)
            previous_results[agent.name] = response.result
            self._memory.set_agent_status(agent.name, response.status)
            self._memory.record_agent_output(
                {
                    "agent": response.agent_name,
                    "objective": response.objective,
                    "reasoning": response.reasoning,
                    "status": response.status,
                    "execution_time_ms": round(response.execution_time_ms, 2),
                    "selected_tools": response.selected_tools,
                    "result": response.result,
                }
            )
            self._memory.record_intermediate_result(
                source=response.agent_name,
                payload={
                    "tool_calls": [asdict(call) for call in response.tool_calls],
                    "result": response.result,
                },
            )

            collaboration_messages.append(
                {
                    "from": agent.name,
                    "to": self.name,
                    "message": "Step complete; returning MCP-backed result payload.",
                }
            )

        completed_at = perf_counter() * 1000
        return {
            "supervisor": {
                "name": self.name,
                "description": self.description,
                "system_prompt": self.system_prompt,
            },
            "plan": plan_payload,
            "agent_outputs": [
                {
                    "agent_name": item.agent_name,
                    "status": item.status,
                    "objective": item.objective,
                    "reasoning": item.reasoning,
                    "selected_tools": item.selected_tools,
                    "tool_calls": [asdict(call) for call in item.tool_calls],
                    "result": item.result,
                    "execution_time_ms": round(item.execution_time_ms, 2),
                }
                for item in agent_outputs
            ],
            "collaboration_messages": collaboration_messages,
            "execution_time_ms": round(completed_at - started_at, 2),
        }
