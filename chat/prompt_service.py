"""Prompt template loading and composition for the execution pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chat.prompt_builder import list_templates


class PromptService:
    """Centralizes prompt templates so each stage stays reusable and testable."""

    def __init__(self) -> None:
        base = Path(__file__).resolve().parent / "prompt_templates"
        self._templates = {
            "system": (base / "system_prompt.txt").read_text(encoding="utf-8"),
            "summary": (base / "summary_prompt.txt").read_text(encoding="utf-8"),
            "intent": (base / "intent_prompt.txt").read_text(encoding="utf-8"),
            "entity": (base / "entity_extraction_prompt.txt").read_text(encoding="utf-8"),
            "response": (base / "response_prompt.txt").read_text(encoding="utf-8"),
        }

    def _persona_instructions(self, template_key: str) -> str:
        templates = {template.key: template.instructions for template in list_templates()}
        return templates.get(template_key, templates.get("customer_assistant", ""))

    @staticmethod
    def _tool_descriptions(available_tools: list[dict]) -> str:
        lines = []
        for tool in available_tools:
            lines.append(
                f"- {tool.get('name', 'unknown_tool')}: {(tool.get('description') or 'No description').strip()}"
            )
        return "\n".join(lines) if lines else "- No tools discovered"

    @staticmethod
    def _render_template(template: str, replacements: dict[str, str]) -> str:
        """Safely render known placeholders without touching literal JSON braces.

        Prompt templates contain JSON examples like {"key": "value"}. Using str.format
        would incorrectly treat those braces as replacement fields. This renderer replaces
        only explicit known tokens such as {conversation_summary}.
        """
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace("{" + key + "}", value)
        return rendered

    def build_summary_prompt(self, *, previous_summary: str, conversation_transcript: str) -> str:
        return self._render_template(
            self._templates["summary"],
            {
                "previous_summary": previous_summary or "No previous summary",
                "conversation_transcript": conversation_transcript,
            },
        )

    def build_intent_prompt(self, *, conversation_summary: str, latest_user_message: str) -> str:
        return self._render_template(
            self._templates["intent"],
            {
                "conversation_summary": conversation_summary or "No summary available",
                "latest_user_message": latest_user_message,
            },
        )

    def build_entity_prompt(self, *, conversation_summary: str, latest_user_message: str) -> str:
        return self._render_template(
            self._templates["entity"],
            {
                "conversation_summary": conversation_summary or "No summary available",
                "latest_user_message": latest_user_message,
            },
        )

    def build_system_prompt(
        self,
        *,
        template_key: str,
        conversation_summary: str,
        intent: dict[str, Any],
        entities: dict[str, Any],
        relevant_context: dict[str, Any],
        available_tools: list[dict],
        referenced_customers: list[Any],
        referenced_orders: list[Any],
    ) -> str:
        return self._render_template(
            self._templates["system"],
            {
                "persona_instructions": self._persona_instructions(template_key),
                "conversation_summary": conversation_summary or "No summary available",
                "intent_json": json.dumps(intent, ensure_ascii=True),
                "entities_json": json.dumps(entities, ensure_ascii=True),
                "relevant_context": json.dumps(relevant_context, ensure_ascii=True),
                "referenced_customers": json.dumps(referenced_customers, ensure_ascii=True),
                "referenced_orders": json.dumps(referenced_orders, ensure_ascii=True),
                "tool_descriptions": self._tool_descriptions(available_tools),
            },
        )

    def build_response_prompt(
        self,
        *,
        latest_user_message: str,
        conversation_summary: str,
        intent: dict[str, Any],
        entities: dict[str, Any],
        tool_results: list[dict[str, Any]],
    ) -> str:
        return self._render_template(
            self._templates["response"],
            {
                "latest_user_message": latest_user_message,
                "conversation_summary": conversation_summary or "No summary available",
                "intent_json": json.dumps(intent, ensure_ascii=True),
                "entities_json": json.dumps(entities, ensure_ascii=True),
                "tool_results_json": json.dumps(tool_results, ensure_ascii=True),
            },
        )
