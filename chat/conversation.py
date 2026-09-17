"""Conversation state primitives for the AI assistant page."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConversationMessage:
    """Single chat message used by Streamlit and OpenAI request assembly."""

    role: str
    content: str


class Conversation:
    """In-memory conversation log for one Streamlit user session."""

    def __init__(self) -> None:
        self._messages: list[ConversationMessage] = []

    @property
    def messages(self) -> list[ConversationMessage]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def add_user(self, content: str) -> None:
        self._messages.append(ConversationMessage(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self._messages.append(ConversationMessage(role="assistant", content=content))

    @staticmethod
    def _message_to_openai_input(message: ConversationMessage) -> dict:
        content_type = "output_text" if message.role == "assistant" else "input_text"
        return {
            "role": message.role,
            "content": [{"type": content_type, "text": message.content}],
        }

    def as_openai_input(self) -> list[dict]:
        return [self._message_to_openai_input(message) for message in self._messages]
