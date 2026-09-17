"""Intent classification service for educational pipeline visibility."""

from __future__ import annotations

import json
from typing import Any

from chat.openai_client import OpenAIClientWrapper
from chat.prompt_service import PromptService


class IntentService:
    """Classifies user intent and whether MCP tools are required."""

    def __init__(self, openai_client: OpenAIClientWrapper, prompt_service: PromptService) -> None:
        self._openai_client = openai_client
        self._prompt_service = prompt_service

    def detect(self, *, conversation_summary: str, latest_user_message: str) -> dict[str, Any]:
        prompt = self._prompt_service.build_intent_prompt(
            conversation_summary=conversation_summary,
            latest_user_message=latest_user_message,
        )
        response = self._openai_client.create_text_response(prompt)
        raw = (response.output_text or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "intent": "General Question",
                "secondary_intent": "",
                "confidence": 0.5,
                "requires_tool": True,
                "tool_category": "None",
                "selection_reason": "Model returned non-JSON output.",
            }
        parsed["_usage"] = self._openai_client.extract_usage(response)
        return parsed
