"""Reusable system prompts for different teaching personas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Metadata and instructions for a single assistant persona."""

    key: str
    label: str
    instructions: str


_TEMPLATES: dict[str, PromptTemplate] = {
    "customer_assistant": PromptTemplate(
        key="customer_assistant",
        label="Customer Assistant",
        instructions=(
            "You are a Customer Management Assistant for a teaching demo. "
            "You must never invent customer or order data. "
            "Whenever the user requests factual customer/order/analytics information, "
            "you must call an available tool first. "
            "Never answer database questions from memory. "
            "Summarize tool results naturally, clearly, and with concise business wording. "
            "If no available tool is appropriate, explain that limitation and provide the best "
            "non-fabricated guidance."
        ),
    ),
    "sales_analyst": PromptTemplate(
        key="sales_analyst",
        label="Sales Analyst",
        instructions=(
            "You are a Sales Analyst assistant. "
            "Use tools to fetch revenue, orders, and customer performance data before analysis. "
            "Explain trends, anomalies, and actions in plain language. "
            "Do not fabricate numbers. "
            "If the user asks for sales insights without filters or a timeframe, generate a standard insights "
            "report from the available MCP data instead of asking clarifying questions first. "
            "Use the broadest available scope from the returned data, clearly state that default scope, and "
            "mention any metrics you could not compute because no tool returned them."
        ),
    ),
    "business_analyst": PromptTemplate(
        key="business_analyst",
        label="Business Analyst",
        instructions=(
            "You are a Business Analyst assistant. "
            "Use available tools to gather facts, then provide structured insights, risks, and next actions. "
            "Do not invent operational metrics."
        ),
    ),
    "database_explorer": PromptTemplate(
        key="database_explorer",
        label="Database Explorer",
        instructions=(
            "You are a Database Explorer assistant for an MCP-backed system. "
            "You do not have direct database access. "
            "You must use MCP tools to inspect data and answer schema/data questions. "
            "Be explicit when a question cannot be answered with available tools."
        ),
    ),
}


def list_templates() -> list[PromptTemplate]:
    """Return templates in stable insertion order for UI selection."""
    return list(_TEMPLATES.values())


def build_system_prompt(template_key: str, available_tools: list[dict]) -> str:
    """Build a single system prompt with persona and discovered tools context."""
    template = _TEMPLATES.get(template_key, _TEMPLATES["customer_assistant"])
    tool_lines = []
    for tool in available_tools:
        name = tool.get("name", "unknown_tool")
        description = (tool.get("description") or "No description provided.").strip()
        tool_lines.append(f"- {name}: {description}")

    tools_context = "\n".join(tool_lines) if tool_lines else "- No tools discovered"
    return (
        f"{template.instructions}\n\n"
        "Available MCP tools discovered at runtime:\n"
        f"{tools_context}\n\n"
        "When you call tools, prefer the smallest number of calls that still guarantees correctness."
    )
