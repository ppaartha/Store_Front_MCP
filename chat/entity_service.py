"""Entity extraction service for structured tool arguments and memory."""

from __future__ import annotations

import json
from typing import Any

from chat.openai_client import OpenAIClientWrapper
from chat.prompt_service import PromptService


class EntityService:
    """Extracts customer/order entities from natural language input."""

    def __init__(self, openai_client: OpenAIClientWrapper, prompt_service: PromptService) -> None:
        self._openai_client = openai_client
        self._prompt_service = prompt_service

    def extract(self, *, conversation_summary: str, latest_user_message: str) -> dict[str, Any]:
        prompt = self._prompt_service.build_entity_prompt(
            conversation_summary=conversation_summary,
            latest_user_message=latest_user_message,
        )
        response = self._openai_client.create_text_response(prompt)
        raw = (response.output_text or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "customer_name": None,
                "country": None,
                "order_id": None,
                "customer_id": None,
                "email": None,
                "date": None,
                "product": None,
                "amount": None,
                "created_after": None,
                "raw": {"unparsed": raw},
            }
        parsed["_usage"] = self._openai_client.extract_usage(response)
        return parsed
