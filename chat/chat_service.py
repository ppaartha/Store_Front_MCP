"""End-to-end AI execution pipeline service for educational observability."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from agents.agent_context import AgentContext
from agents.agent_registry import AgentRegistry
from agents.analytics_agent import AnalyticsAgent
from agents.customer_agent import CustomerAgent
from agents.memory_manager import AgentMemoryManager
from agents.order_agent import OrderAgent
from agents.planner import Planner
from agents.supervisor_agent import SupervisorAgent
from chat.conversation_service import ConversationService
from chat.entity_service import EntityService
from chat.intent_service import IntentService
from chat.openai_client import OpenAIClientWrapper
from chat.prompt_service import PromptService
from chat.summary_service import SummaryService
from chat.tool_executor import MCPToolExecutor, ToolExecutionRecord

logger = logging.getLogger("ai.pipeline")


@dataclass(slots=True)
class PipelineStageData:
    """UI payload for one explainable pipeline stage."""

    name: str
    payload: dict[str, Any]


@dataclass(slots=True)
class PipelineResult:
    """Complete execution data returned to Streamlit per user message."""

    stages: list[PipelineStageData] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    tool_records: list[ToolExecutionRecord] = field(default_factory=list)
    response_prompt: str = ""
    fallback_response_text: str = ""
    usage: dict[str, int] = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})


class ChatService:
    """Coordinates all pipeline stages before final answer streaming."""

    def __init__(
        self,
        *,
        openai_client: OpenAIClientWrapper,
        prompt_service: PromptService,
        summary_service: SummaryService,
        intent_service: IntentService,
        entity_service: EntityService,
        tool_executor: MCPToolExecutor,
        max_tool_rounds: int = 8,
    ) -> None:
        self._openai_client = openai_client
        self._prompt_service = prompt_service
        self._summary_service = summary_service
        self._intent_service = intent_service
        self._entity_service = entity_service
        self._tool_executor = tool_executor
        self._max_tool_rounds = max_tool_rounds

    @staticmethod
    def _conversation_transcript(messages: list[Any]) -> str:
        lines = []
        for message in messages:
            role = getattr(message, "role", "unknown")
            content = getattr(message, "content", "")
            lines.append(f"{role.upper()}: {content}")
        return "\n".join(lines[-20:])

    @staticmethod
    def _extract_tool_calls(response: Any) -> list[dict[str, Any]]:
        output = getattr(response, "output", None) or []
        tool_calls: list[dict[str, Any]] = []
        for item in output:
            if getattr(item, "type", None) != "function_call":
                continue
            raw_arguments = getattr(item, "arguments", "{}") or "{}"
            try:
                arguments = json.loads(raw_arguments)
                if not isinstance(arguments, dict):
                    arguments = {"value": arguments}
            except json.JSONDecodeError:
                arguments = {"_raw_arguments": raw_arguments}

            tool_calls.append(
                {
                    "name": getattr(item, "name", "unknown_tool"),
                    "call_id": getattr(item, "call_id", ""),
                    "arguments": arguments,
                }
            )
        return tool_calls

    @staticmethod
    def _looks_like_sales_insight_request(user_message: str, intent: dict[str, Any]) -> bool:
        text = user_message.lower()
        intent_text = str(intent.get("intent", "")).lower()
        tool_category = str(intent.get("tool_category", "")).lower()

        sales_terms = [
            "sales insight",
            "sales insights",
            "revenue insight",
            "revenue insights",
            "sales report",
            "sales analysis",
            "generate sales",
        ]
        return (
            any(term in text for term in sales_terms)
            or "sales" in intent_text
            or "revenue" in intent_text
            or "sales" in tool_category
            or "analytics" in tool_category
        )

    @staticmethod
    def _find_tool_name(available_tools: list[dict[str, Any]], preferred_names: list[str]) -> str | None:
        names = {str(tool.get("name", "")) for tool in available_tools}
        for name in preferred_names:
            if name in names:
                return name
        return None

    def agent_catalog(self) -> list[dict[str, Any]]:
        """Return registered specialist metadata for UI monitoring."""
        registry = AgentRegistry()
        registry.register(CustomerAgent(openai_client=self._openai_client, tool_executor=self._tool_executor))
        registry.register(OrderAgent(openai_client=self._openai_client, tool_executor=self._tool_executor))
        registry.register(AnalyticsAgent(openai_client=self._openai_client, tool_executor=self._tool_executor))
        return [
            {
                "name": "supervisor_agent",
                "description": "Coordinates planning, delegation, and final response composition.",
                "capabilities": [
                    "goal understanding",
                    "task planning",
                    "delegation",
                    "result synthesis",
                ],
            },
            *registry.summaries(),
        ]

    def process_turn(
        self,
        *,
        conversation_service: ConversationService,
        latest_user_message: str,
        template_key: str,
    ) -> PipelineResult:
        state = conversation_service.state
        result = PipelineResult()

        # Stage 1: conversation history snapshot
        history_payload = {
            "messages": [{"role": m.role, "content": m.content} for m in state.conversation.messages],
            "message_count": len(state.conversation.messages),
            "token_estimate": conversation_service.token_estimate(),
        }
        result.stages.append(PipelineStageData(name="Conversation History", payload=history_payload))
        result.timeline.append("Conversation history collected")
        conversation_service.log_event(
            "stage",
            "Conversation history collected",
            {"message_count": history_payload["message_count"], "token_estimate": history_payload["token_estimate"]},
        )

        # Stage 2: summary generation
        summary_raw = self._summary_service.summarize(
            previous_summary=state.current_summary,
            conversation_transcript=self._conversation_transcript(state.conversation.messages),
        )
        summary_usage = summary_raw.pop("_usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        conversation_service.update_summary(
            new_summary=str(summary_raw.get("current_summary", "")),
            known_entities=summary_raw.get("known_entities", {}) or {},
            pending_tasks=summary_raw.get("pending_tasks", []) or [],
            state=str(summary_raw.get("conversation_state", "open")),
        )
        result.stages.append(
            PipelineStageData(
                name="Conversation Summary",
                payload={
                    "previous_summary": state.previous_summary,
                    "current_summary": state.current_summary,
                    "summary_updates": state.summary_updates,
                    "current_objective": summary_raw.get("current_objective", ""),
                    "pending_tasks": state.pending_tasks,
                    "conversation_state": state.conversation_state,
                },
            )
        )
        result.timeline.append("Conversation summarized")
        conversation_service.log_event(
            "stage",
            "Conversation summary updated",
            {"conversation_state": state.conversation_state, "pending_tasks": state.pending_tasks},
        )

        # Stage 3: intent detection
        intent_raw = self._intent_service.detect(
            conversation_summary=state.current_summary,
            latest_user_message=latest_user_message,
        )
        intent_usage = intent_raw.pop("_usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        intent_label = str(intent_raw.get("intent", "General Question"))
        conversation_service.register_intent(intent_label)
        result.stages.append(PipelineStageData(name="Intent Detection", payload=intent_raw))
        result.timeline.append("Intent classified")
        conversation_service.log_event(
            "stage",
            "Intent detected",
            {"intent": intent_label, "confidence": intent_raw.get("confidence", 0.0)},
        )

        # Stage 4: entity extraction
        entities_raw = self._entity_service.extract(
            conversation_summary=state.current_summary,
            latest_user_message=latest_user_message,
        )
        entities_usage = entities_raw.pop("_usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        conversation_service.update_references(entities_raw)
        result.stages.append(PipelineStageData(name="Entity Extraction", payload=entities_raw))
        result.timeline.append("Entities extracted")
        conversation_service.log_event("stage", "Entities extracted", entities_raw)

        # Stage 5: relevant context selection
        relevant_context = {
            "conversation_context": state.current_summary,
            "required_database_context": intent_raw.get("tool_category", "None"),
            "relevant_mcp_resources": ["customer://all", "orders://summary", "orders://recent"],
            "previous_references": {
                "customers": state.referenced_customers,
                "orders": state.referenced_orders,
            },
            "previous_tool_calls": state.previous_tool_calls[-5:],
            "default_analytics_scope": {
                "timeframe": "all available data unless a tool specifically returns recent-window metrics",
                "dimensions": ["revenue", "orders", "top customers", "geography", "recent activity"],
                "behavior": "produce a standard report when user asks for generic sales insights",
            },
        }
        result.stages.append(PipelineStageData(name="Relevant Context", payload=relevant_context))
        result.timeline.append("Relevant context selected")
        conversation_service.log_event("stage", "Relevant context assembled")

        # Stage 6: MCP tool discovery + shared client context
        tool_discovery_error: str | None = None
        try:
            available_tools = self._tool_executor.list_tools()
        except Exception as exc:
            tool_discovery_error = str(exc)
            logger.exception("pipeline_tool_discovery_failed error=%s", tool_discovery_error)
            available_tools = []

        system_prompt = self._prompt_service.build_system_prompt(
            template_key=template_key,
            conversation_summary=state.current_summary,
            intent=intent_raw,
            entities=entities_raw,
            relevant_context=relevant_context,
            available_tools=available_tools,
            referenced_customers=state.referenced_customers,
            referenced_orders=state.referenced_orders,
        )

        prompt_payload = {
            "system_prompt": system_prompt,
            "conversation_summary": state.current_summary,
            "recent_messages": history_payload["messages"][-6:],
            "tool_descriptions": available_tools,
            "user_message": latest_user_message,
            "tool_discovery_error": tool_discovery_error,
        }
        result.stages.append(PipelineStageData(name="Prompt Construction", payload=prompt_payload))
        result.timeline.append("Prompt built")
        conversation_service.log_event(
            "stage",
            "Prompt constructed",
            {"tool_count": len(available_tools), "template": template_key},
        )

        if tool_discovery_error:
            result.stages.append(
                PipelineStageData(
                    name="Tool Selection",
                    payload={
                        "available_tools": [],
                        "selected_tools": [],
                        "error": tool_discovery_error,
                    },
                )
            )
            result.timeline.append("Tool discovery failed")
            conversation_service.log_event(
                "error",
                "MCP tool discovery failed",
                {"error": tool_discovery_error},
            )

            result.stages.append(
                PipelineStageData(
                    name="MCP Execution",
                    payload={
                        "executions": [],
                        "error": "Skipped because MCP tool discovery failed.",
                    },
                )
            )
            result.timeline.append("MCP execution skipped")

            tool_results = [
                {
                    "tool": "mcp_tool_discovery",
                    "success": False,
                    "response": None,
                    "error": tool_discovery_error,
                    "duration_ms": 0.0,
                }
            ]
            response_prompt = self._prompt_service.build_response_prompt(
                latest_user_message=latest_user_message,
                conversation_summary=state.current_summary,
                intent=intent_raw,
                entities=entities_raw,
                tool_results=tool_results,
            )
            result.response_prompt = response_prompt
            result.stages.append(
                PipelineStageData(
                    name="Response Generation",
                    payload={
                        "tool_result": tool_results,
                        "response_prompt": response_prompt,
                        "final_response": "Generated via streaming",
                    },
                )
            )
            result.timeline.append("Response generated")

            result.usage = {
                "prompt_tokens": summary_usage.get("prompt_tokens", 0)
                + intent_usage.get("prompt_tokens", 0)
                + entities_usage.get("prompt_tokens", 0),
                "completion_tokens": summary_usage.get("completion_tokens", 0)
                + intent_usage.get("completion_tokens", 0)
                + entities_usage.get("completion_tokens", 0),
                "total_tokens": summary_usage.get("total_tokens", 0)
                + intent_usage.get("total_tokens", 0)
                + entities_usage.get("total_tokens", 0),
            }
            logger.info("pipeline_complete_with_discovery_failure intent=%s", intent_label)
            return result

        # Stage 7: planning + supervisor decision
        planning_started = perf_counter()
        memory_manager = AgentMemoryManager(conversation_service)
        planner = Planner()
        registry = AgentRegistry()
        registry.register(CustomerAgent(openai_client=self._openai_client, tool_executor=self._tool_executor))
        registry.register(OrderAgent(openai_client=self._openai_client, tool_executor=self._tool_executor))
        registry.register(AnalyticsAgent(openai_client=self._openai_client, tool_executor=self._tool_executor))

        supervisor = SupervisorAgent(
            planner=planner,
            registry=registry,
            memory_manager=memory_manager,
        )
        base_context = AgentContext(
            user_request=latest_user_message,
            conversation_summary=state.current_summary,
            conversation_memory=memory_manager.build_memory_snapshot(),
            relevant_entities=entities_raw,
            intent=intent_raw,
            previous_results={},
            current_plan=[],
        )

        supervisor_output = supervisor.execute(base_context)
        planning_duration_ms = (perf_counter() - planning_started) * 1000
        conversation_service.add_planning_duration(planning_duration_ms)
        conversation_service.add_collaboration_messages(supervisor_output.get("collaboration_messages", []))
        conversation_service.log_event(
            "planning",
            "Execution plan generated",
            {
                "plan_step_count": len(supervisor_output.get("plan", [])),
                "planning_time_ms": round(planning_duration_ms, 2),
            },
        )

        result.stages.append(
            PipelineStageData(
                name="Planning",
                payload={
                    "goal": latest_user_message,
                    "planner": "Planner",
                    "plan": supervisor_output.get("plan", []),
                    "planning_time_ms": round(planning_duration_ms, 2),
                },
            )
        )
        result.timeline.append("Plan generated")

        selected_agents = [step.get("agent", "") for step in supervisor_output.get("plan", [])]
        result.stages.append(
            PipelineStageData(
                name="Supervisor Decision",
                payload={
                    "supervisor": supervisor_output.get("supervisor", {}),
                    "selected_agents": selected_agents,
                    "execution_order": supervisor_output.get("plan", []),
                },
            )
        )
        result.timeline.append("Supervisor decided delegation")
        conversation_service.log_event(
            "delegation",
            "Supervisor selected specialist agents",
            {"selected_agents": selected_agents},
        )

        result.stages.append(
            PipelineStageData(
                name="Task Delegation",
                payload={
                    "collaboration_messages": supervisor_output.get("collaboration_messages", []),
                },
            )
        )
        result.timeline.append("Tasks delegated")
        conversation_service.log_event(
            "delegation",
            "Task delegation messages emitted",
            {"message_count": len(supervisor_output.get("collaboration_messages", []))},
        )

        agent_outputs = supervisor_output.get("agent_outputs", [])
        result.stages.append(
            PipelineStageData(
                name="Agent Execution",
                payload={
                    "running_agent": "none",
                    "completed_agents": [a.get("agent_name", "") for a in agent_outputs],
                    "agent_outputs": agent_outputs,
                },
            )
        )
        result.timeline.append("Agents executed")
        conversation_service.log_event(
            "agent_execution",
            "Specialist agent execution completed",
            {"agent_count": len(agent_outputs)},
        )

        tool_selection_events: list[dict[str, Any]] = []
        for agent_output in agent_outputs:
            for call in agent_output.get("tool_calls", []):
                tool_name = str(call.get("tool_name", ""))
                arguments = call.get("arguments", {}) or {}
                success = bool(call.get("success", False))
                duration_ms = float(call.get("duration_ms", 0.0) or 0.0)
                response_payload = call.get("response")
                error = call.get("error")

                tool_selection_events.append(
                    {
                        "agent": agent_output.get("agent_name", "unknown_agent"),
                        "selected_tool": tool_name,
                        "selection_reason": agent_output.get("reasoning", ""),
                        "arguments": arguments,
                        "confidence": intent_raw.get("confidence", 0.0),
                        "execution_order": len(tool_selection_events) + 1,
                    }
                )

                conversation_service.register_tool_usage(tool_name)
                conversation_service.add_tool_call(
                    {
                        "tool": tool_name,
                        "arguments": arguments,
                        "success": success,
                        "response": response_payload if success else {"error": error},
                        "duration_ms": duration_ms,
                    }
                )

                result.tool_records.append(
                    ToolExecutionRecord(
                        tool_name=tool_name,
                        arguments=arguments,
                        duration_ms=duration_ms,
                        success=success,
                        response=response_payload,
                        error=error,
                    )
                )
                conversation_service.log_event(
                    "tool_call",
                    f"{agent_output.get('agent_name', 'unknown_agent')} executed {tool_name}",
                    {
                        "tool": tool_name,
                        "success": success,
                        "duration_ms": round(duration_ms, 2),
                    },
                )

        # Keep deterministic fallback for generic sales prompts if delegation produced no tools.
        if not result.tool_records and self._looks_like_sales_insight_request(latest_user_message, intent_raw):
            fallback_tool_name = self._find_tool_name(available_tools, ["generate_sales_insights", "sales_summary"])
            if fallback_tool_name:
                record = self._tool_executor.execute_tool(fallback_tool_name, {})
                tool_selection_events.append(
                    {
                        "agent": "analytics_agent",
                        "selected_tool": fallback_tool_name,
                        "selection_reason": "Fallback default for generic sales-insight request.",
                        "arguments": {},
                        "confidence": intent_raw.get("confidence", 0.0),
                        "execution_order": len(tool_selection_events) + 1,
                        "fallback": True,
                    }
                )
                conversation_service.register_tool_usage(fallback_tool_name)
                conversation_service.add_tool_call(
                    {
                        "tool": record.tool_name,
                        "arguments": record.arguments,
                        "success": record.success,
                        "response": record.response if record.success else {"error": record.error},
                        "duration_ms": record.duration_ms,
                    }
                )
                result.tool_records.append(record)
                conversation_service.log_event(
                    "tool_call",
                    f"Fallback analytics tool executed: {fallback_tool_name}",
                    {
                        "tool": fallback_tool_name,
                        "success": record.success,
                        "duration_ms": round(record.duration_ms, 2),
                        "fallback": True,
                    },
                )

        result.stages.append(
            PipelineStageData(
                name="Tool Selection",
                payload={
                    "available_tools": [tool.get("name", "") for tool in available_tools],
                    "selected_tools": tool_selection_events,
                },
            )
        )
        result.timeline.append("Tools selected")

        result.stages.append(
            PipelineStageData(
                name="MCP Execution",
                payload={
                    "executions": [
                        {
                            "request": {"tool": r.tool_name, "arguments": r.arguments},
                            "execution_time_ms": round(r.duration_ms, 2),
                            "returned_json": r.response if r.success else {"error": r.error},
                            "success": r.success,
                        }
                        for r in result.tool_records
                    ]
                },
            )
        )
        result.timeline.append("MCP tools executed")
        conversation_service.log_event(
            "stage",
            "MCP tool execution complete",
            {"tool_calls": len(result.tool_records)},
        )

        # Stage 9: final response generation prompt (for streaming step)
        tool_results = [
            {
                "tool": r.tool_name,
                "success": r.success,
                "response": r.response,
                "error": r.error,
                "duration_ms": round(r.duration_ms, 2),
            }
            for r in result.tool_records
        ]
        response_prompt = self._prompt_service.build_response_prompt(
            latest_user_message=latest_user_message,
            conversation_summary=state.current_summary,
            intent=intent_raw,
            entities=entities_raw,
            tool_results=tool_results,
        )
        result.response_prompt = response_prompt
        result.stages.append(
            PipelineStageData(
                name="Response Generation",
                payload={
                    "tool_result": tool_results,
                    "agent_collaboration": supervisor_output.get("collaboration_messages", []),
                    "agent_outputs": supervisor_output.get("agent_outputs", []),
                    "response_prompt": response_prompt,
                    "final_response": "Generated via streaming",
                },
            )
        )
        result.timeline.append("Response generated")
        conversation_service.log_event(
            "stage",
            "Final response prompt generated",
            {"tool_result_count": len(tool_results)},
        )

        # Aggregate usage counters from non-stream stages.
        result.usage = {
            "prompt_tokens": summary_usage.get("prompt_tokens", 0)
            + intent_usage.get("prompt_tokens", 0)
            + entities_usage.get("prompt_tokens", 0),
            "completion_tokens": summary_usage.get("completion_tokens", 0)
            + intent_usage.get("completion_tokens", 0)
            + entities_usage.get("completion_tokens", 0),
            "total_tokens": summary_usage.get("total_tokens", 0)
            + intent_usage.get("total_tokens", 0)
            + entities_usage.get("total_tokens", 0),
        }

        logger.info("pipeline_complete intent=%s tools=%s", intent_label, len(result.tool_records))
        return result
