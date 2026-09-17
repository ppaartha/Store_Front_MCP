"""High-level chat orchestrator connecting OpenAI tool-calling to MCP."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from chat.conversation import Conversation
from chat.openai_client import OpenAIClientWrapper
from chat.prompt_builder import build_system_prompt
from chat.tool_executor import MCPToolExecutor, ToolExecutionRecord

logger = logging.getLogger("ai.assistant")


@dataclass(slots=True)
class ChatTurnResult:
    """Output bundle returned to the Streamlit page for rendering."""

    assistant_text: str
    tool_records: list[ToolExecutionRecord]
    flow_steps: list[dict[str, Any]]


class CustomerAssistantChatbot:
    """Coordinates prompt construction, tool execution, and final response generation."""

    def __init__(
        self,
        *,
        openai_client: OpenAIClientWrapper,
        tool_executor: MCPToolExecutor,
        max_tool_rounds: int = 8,
    ) -> None:
        self._openai_client = openai_client
        self._tool_executor = tool_executor
        self._max_tool_rounds = max_tool_rounds

    @staticmethod
    def _extract_tool_calls(response: Any) -> list[dict]:
        output = getattr(response, "output", None) or []
        tool_calls: list[dict] = []

        for item in output:
            item_type = getattr(item, "type", None)
            if item_type != "function_call":
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
    def _extract_text(response: Any) -> str:
        output_text = getattr(response, "output_text", "")
        if output_text:
            return str(output_text)

        output = getattr(response, "output", None) or []
        parts: list[str] = []
        for item in output:
            if getattr(item, "type", None) != "message":
                continue
            content = getattr(item, "content", None) or []
            for chunk in content:
                text = getattr(chunk, "text", None)
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()

    def run_turn(self, conversation: Conversation, *, template_key: str) -> ChatTurnResult:
        """Run one full assistant turn, including zero or more tool-calling rounds."""
        user_prompt = conversation.messages[-1].content if conversation.messages else ""
        logger.info("assistant_turn_start template=%s prompt=%s", template_key, user_prompt)

        discovered_tools = self._tool_executor.list_tools()
        system_prompt = build_system_prompt(template_key, discovered_tools)

        flow_steps: list[dict[str, Any]] = [
            {"stage": "user_prompt", "detail": user_prompt},
            {"stage": "openai_request", "detail": "Responses API with auto tool_choice"},
        ]

        response = self._openai_client.create_response(
            input_items=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                *conversation.as_openai_input(),
            ],
            tools=discovered_tools,
            previous_response_id=None,
        )

        tool_records: list[ToolExecutionRecord] = []
        rounds = 0
        while rounds < self._max_tool_rounds:
            rounds += 1
            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                break

            followup_items: list[dict] = []
            for call in tool_calls:
                flow_steps.append({"stage": "tool_selected", "detail": call["name"]})
                flow_steps.append({"stage": "mcp_request", "detail": call["arguments"]})

                record = self._tool_executor.execute_tool(call["name"], call["arguments"])
                tool_records.append(record)

                flow_steps.append(
                    {
                        "stage": "tool_response",
                        "detail": {
                            "success": record.success,
                            "tool": record.tool_name,
                            "error": record.error,
                        },
                    }
                )

                followup_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": self._tool_executor.format_tool_output_for_openai(record),
                    }
                )

            response = self._openai_client.create_response(
                input_items=followup_items,
                tools=discovered_tools,
                previous_response_id=getattr(response, "id", None),
            )

        assistant_text = self._extract_text(response)
        if not assistant_text:
            assistant_text = "I could not produce a final answer. Please try rephrasing the request."

        flow_steps.append({"stage": "final_response", "detail": assistant_text})
        logger.info("assistant_final_response=%s", assistant_text)

        return ChatTurnResult(
            assistant_text=assistant_text,
            tool_records=tool_records,
            flow_steps=flow_steps,
        )
