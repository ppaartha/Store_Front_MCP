"""OpenAI Responses API wrapper with retries and model configuration."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

logger = logging.getLogger("ai.assistant.openai")


@dataclass(frozen=True, slots=True)
class OpenAISettings:
    """Configuration for model behavior and reliability controls."""

    api_key: str
    model: str
    temperature: float | None = None
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0


class OpenAIClientWrapper:
    """Thin wrapper so chat orchestration logic stays framework-agnostic."""

    def __init__(self, settings: OpenAISettings) -> None:
        self._settings = settings
        self._client = OpenAI(api_key=settings.api_key)

    @staticmethod
    def _is_unsupported_temperature_error(exc: Exception) -> bool:
        return "Unsupported parameter: 'temperature'" in str(exc)

    def create_response(
        self,
        *,
        input_items: list[dict],
        tools: list[dict],
        previous_response_id: str | None = None,
    ) -> Any:
        """Create one Responses API turn with retries for transient failures."""
        attempt = 0
        while True:
            attempt += 1
            try:
                kwargs: dict[str, Any] = {
                    "model": self._settings.model,
                    "input": input_items,
                    "tools": tools,
                    "tool_choice": "auto",
                    "previous_response_id": previous_response_id,
                }
                if self._settings.temperature is not None:
                    kwargs["temperature"] = self._settings.temperature
                return self._client.responses.create(**kwargs)
            except Exception as exc:
                if self._is_unsupported_temperature_error(exc):
                    logger.warning("openai_model_rejects_temperature retrying_without_temperature")
                    return self._client.responses.create(
                        model=self._settings.model,
                        input=input_items,
                        tools=tools,
                        tool_choice="auto",
                        previous_response_id=previous_response_id,
                    )
                if attempt >= self._settings.max_retries:
                    raise
                sleep_seconds = self._settings.retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "openai_retry attempt=%s sleep_seconds=%.2f",
                    attempt,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)

    def create_text_response(self, prompt: str) -> Any:
        """Create a plain text response without tool definitions."""
        attempt = 0
        while True:
            attempt += 1
            try:
                kwargs: dict[str, Any] = {
                    "model": self._settings.model,
                    "input": [
                        {
                            "role": "user",
                            "content": [{"type": "input_text", "text": prompt}],
                        }
                    ],
                }
                if self._settings.temperature is not None:
                    kwargs["temperature"] = self._settings.temperature
                return self._client.responses.create(**kwargs)
            except Exception as exc:
                if self._is_unsupported_temperature_error(exc):
                    logger.warning("openai_model_rejects_temperature retrying_without_temperature")
                    return self._client.responses.create(
                        model=self._settings.model,
                        input=[
                            {
                                "role": "user",
                                "content": [{"type": "input_text", "text": prompt}],
                            }
                        ],
                    )
                if attempt >= self._settings.max_retries:
                    raise
                sleep_seconds = self._settings.retry_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "openai_text_retry attempt=%s sleep_seconds=%.2f",
                    attempt,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)

    def stream_text_response(self, prompt: str):
        """Yield text deltas from OpenAI streaming for real-time UI rendering."""
        def _iterate_stream(with_temperature: bool):
            kwargs: dict[str, Any] = {
                "model": self._settings.model,
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    }
                ],
            }
            if with_temperature and self._settings.temperature is not None:
                kwargs["temperature"] = self._settings.temperature

            with self._client.responses.stream(**kwargs) as stream:
                for event in stream:
                    event_type = getattr(event, "type", "")
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, "delta", "")
                        if delta:
                            yield str(delta)

        try:
            yield from _iterate_stream(with_temperature=True)
            return
        except Exception as exc:
            if not self._is_unsupported_temperature_error(exc):
                raise
            logger.warning("openai_model_rejects_temperature streaming_without_temperature")
            yield from _iterate_stream(with_temperature=False)

    @staticmethod
    def extract_usage(response: Any) -> dict[str, int]:
        """Extract usage counters defensively across SDK versions."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        return {
            "prompt_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        }
