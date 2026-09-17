"""Application entrypoint for running the MCP server."""

from __future__ import annotations

import logging

from config import get_settings
from seed import bootstrap
from server import mcp

settings = get_settings()


def configure_logging() -> None:
    """Configure process-wide logging for MCP request traces and app diagnostics."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main() -> None:
    configure_logging()
    bootstrap(migrate=True, force_reseed=False)

    # FastMCP's internal settings may keep their own defaults, so set the
    # network binding explicitly before starting the server.
    mcp.settings.host = settings.mcp_host
    mcp.settings.port = settings.mcp_port
    mcp.settings.log_level = settings.log_level.upper()

    # Docker Compose reaches the server via the service hostname `mcp-server`.
    # FastMCP protects against DNS rebinding by default, so permit that host
    # header explicitly for this teaching/demo environment.
    if mcp.settings.transport_security is not None:
        allowed_hosts = list(mcp.settings.transport_security.allowed_hosts)
        for host_pattern in ["mcp-server:*", "customer_order_mcp_server:*"]:
            if host_pattern not in allowed_hosts:
                allowed_hosts.append(host_pattern)
        mcp.settings.transport_security.allowed_hosts = allowed_hosts

    # FastMCP streamable-http requires its own lifecycle manager to initialize
    # internal task groups. Running through mcp.run avoids "Task group is not
    # initialized" errors that can happen when directly mounting ASGI internals.
    mcp.run(transport=settings.mcp_transport, mount_path="/mcp")


if __name__ == "__main__":
    main()
