"""Dynamic MCP tool discovery and execution for OpenAI tool calling."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger("ai.assistant.mcp")


@dataclass(slots=True)
class ToolExecutionRecord:
    """UI-visible metadata for one tool call."""

    tool_name: str
    arguments: dict[str, Any]
    duration_ms: float
    success: bool
    response: Any
    error: str | None = None


class MCPToolExecutor:
    """Fetch tools from MCP at runtime and execute them without hardcoding."""

    def __init__(self, mcp_server_url: str, timeout_seconds: float = 25.0) -> None:
        self._mcp_server_url = mcp_server_url
        self._timeout_seconds = timeout_seconds
        self._candidate_urls = self._build_candidate_urls(mcp_server_url)
        self._active_url: str | None = None

    @staticmethod
    def _normalize_url(url: str) -> str:
        return url.strip().rstrip("/")

    @classmethod
    def _build_candidate_urls(cls, primary_url: str) -> list[str]:
        """Build a small list of MCP endpoint candidates for local/docker runs."""
        primary = cls._normalize_url(primary_url)
        candidates = [primary]

        parsed = urlparse(primary)
        path = parsed.path.rstrip("/")
        if path != "/mcp":
            candidates.append(
                urlunparse(
                    (
                        parsed.scheme,
                        parsed.netloc,
                        "/mcp",
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
            )

        hostname = (parsed.hostname or "").lower()
        netloc = parsed.netloc
        if hostname in {"localhost", "127.0.0.1"}:
            docker_netloc = netloc.replace(hostname, "mcp-server", 1)
            candidates.append(
                urlunparse(
                    (
                        parsed.scheme,
                        docker_netloc,
                        path or "/mcp",
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
            )
        elif hostname == "mcp-server":
            local_netloc = netloc.replace("mcp-server", "localhost", 1)
            candidates.append(
                urlunparse(
                    (
                        parsed.scheme,
                        local_netloc,
                        path or "/mcp",
                        parsed.params,
                        parsed.query,
                        parsed.fragment,
                    )
                )
            )

        deduped: list[str] = []
        seen: set[str] = set()
        for url in candidates:
            normalized = cls._normalize_url(url)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [MCPToolExecutor._to_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {str(k): MCPToolExecutor._to_jsonable(v) for k, v in value.items()}
        if hasattr(value, "model_dump"):
            return MCPToolExecutor._to_jsonable(value.model_dump(mode="json"))
        if hasattr(value, "dict"):
            return MCPToolExecutor._to_jsonable(value.dict())
        if hasattr(value, "__dict__"):
            return MCPToolExecutor._to_jsonable(vars(value))
        return str(value)

    @staticmethod
    def _format_exception(exc: Exception) -> str:
        """Flatten nested exception groups into a readable single-line error."""
        if isinstance(exc, BaseExceptionGroup):
            parts: list[str] = []
            for child in exc.exceptions:
                if isinstance(child, Exception):
                    parts.append(MCPToolExecutor._format_exception(child))
                else:
                    parts.append(str(child))
            return " | ".join(part for part in parts if part) or str(exc)
        return str(exc)

    async def _list_tools_async(self, url: str) -> list[dict]:
        async with streamablehttp_client(url) as streams:
            read_stream, write_stream, *_ = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = getattr(result, "tools", [])

                openai_tools: list[dict] = []
                for tool in tools:
                    input_schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
                    openai_tools.append(
                        {
                            "type": "function",
                            "name": getattr(tool, "name", "unknown_tool"),
                            "description": getattr(tool, "description", ""),
                            "parameters": self._to_jsonable(input_schema),
                        }
                    )
                return openai_tools

    async def _call_tool_async(self, url: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        async with streamablehttp_client(url) as streams:
            read_stream, write_stream, *_ = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return self._to_jsonable(result)

    def list_tools(self) -> list[dict]:
        """Discover MCP tools and map each schema into OpenAI function format."""
        errors: list[str] = []
        ordered_candidates = ([self._active_url] if self._active_url else []) + [
            url for url in self._candidate_urls if url != self._active_url
        ]

        for candidate_url in ordered_candidates:
            try:
                tools = asyncio.run(
                    asyncio.wait_for(self._list_tools_async(candidate_url), timeout=self._timeout_seconds)
                )
                self._active_url = candidate_url
                return tools
            except Exception as exc:
                message = self._format_exception(exc)
                errors.append(f"{candidate_url} -> {message}")
                logger.warning("tool_discovery_candidate_failed url=%s error=%s", candidate_url, message)

        message = " ; ".join(errors) if errors else "unknown discovery failure"
        logger.exception("tool_discovery_failure error=%s", message)
        raise RuntimeError(f"MCP tool discovery failed: {message}")

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> ToolExecutionRecord:
        """Execute one MCP tool call with telemetry for educational visibility."""
        started = time.perf_counter()
        logger.info("tool_call_start tool=%s args=%s", tool_name, arguments)
        ordered_candidates = ([self._active_url] if self._active_url else []) + [
            url for url in self._candidate_urls if url != self._active_url
        ]
        errors: list[str] = []

        for candidate_url in ordered_candidates:
            try:
                response = asyncio.run(
                    asyncio.wait_for(
                        self._call_tool_async(
                            url=candidate_url,
                            tool_name=tool_name,
                            arguments=arguments,
                        ),
                        timeout=self._timeout_seconds,
                    )
                )
                self._active_url = candidate_url
                duration_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "tool_call_success tool=%s duration_ms=%.2f url=%s response=%s",
                    tool_name,
                    duration_ms,
                    candidate_url,
                    response,
                )
                return ToolExecutionRecord(
                    tool_name=tool_name,
                    arguments=arguments,
                    duration_ms=duration_ms,
                    success=True,
                    response=response,
                )
            except Exception as exc:
                message = self._format_exception(exc)
                errors.append(f"{candidate_url} -> {message}")
                logger.warning(
                    "tool_call_candidate_failed tool=%s url=%s error=%s",
                    tool_name,
                    candidate_url,
                    message,
                )

        duration_ms = (time.perf_counter() - started) * 1000
        logger.exception("tool_call_failure tool=%s duration_ms=%.2f", tool_name, duration_ms)
        return ToolExecutionRecord(
            tool_name=tool_name,
            arguments=arguments,
            duration_ms=duration_ms,
            success=False,
            response=None,
            error=" ; ".join(errors) if errors else "unknown tool call failure",
        )

    @staticmethod
    def format_tool_output_for_openai(record: ToolExecutionRecord) -> str:
        """Render output payload for function_call_output input item."""
        payload = {
            "tool": record.tool_name,
            "success": record.success,
            "duration_ms": round(record.duration_ms, 2),
            "response": record.response,
            "error": record.error,
        }
        return json.dumps(payload, ensure_ascii=True)
