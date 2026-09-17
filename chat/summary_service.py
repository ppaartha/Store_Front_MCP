"""Conversation summarization service using OpenAI."""

from __future__ import annotations

import json
from typing import Any

from chat.openai_client import OpenAIClientWrapper
from chat.prompt_service import PromptService


class SummaryService:
    """Compresses long chat history into a reusable memory summary."""

    def __init__(self, openai_client: OpenAIClientWrapper, prompt_service: PromptService) -> None:
        self._openai_client = openai_client
        self._prompt_service = prompt_service

    def summarize(self, *, previous_summary: str, conversation_transcript: str) -> dict[str, Any]:
        prompt = self._prompt_service.build_summary_prompt(
            previous_summary=previous_summary,
            conversation_transcript=conversation_transcript,
        )
        response = self._openai_client.create_text_response(prompt)
        raw = (response.output_text or "").strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "current_summary": raw or "Summary unavailable",
                "current_objective": "Unknown",
                "known_entities": {},
                "pending_tasks": [],
                "conversation_state": "open",
            }
        parsed["_usage"] = self._openai_client.extract_usage(response)
        return parsed
