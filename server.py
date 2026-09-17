"""FastMCP server wiring and service container."""

from __future__ import annotations

import logging
from typing import Self

from mcp.server.fastmcp import FastMCP

from database import get_session
from repositories import CustomerRepository, OrderRepository, SalesRepository
from resources import register_resources
from prompts import register_prompts
from services import AnalyticsService, CustomerService, OrderService
from tools import register_tools

logger = logging.getLogger(__name__)

mcp = FastMCP("Customer Order MCP Server")


class ServiceFactory:
    """Factory that creates service objects backed by one transaction/session."""

    def __init__(self):
        # This method runs when we create ServiceFactory().
        # We initialize placeholders so each request can store its own DB session and services.
        # Think of this as preparing an empty "toolbox" for one unit of work.
        self._session_context = None
        self.session = None
        self.customer_service = None
        self.order_service = None
        self.analytics_service = None

    def __enter__(self) -> Self:
        # __enter__ runs automatically when we use:
        #   with ServiceFactory() as factory:
        # This is where we open database access for the current request.

        # get_session() returns a context manager that handles commit/rollback/close safely.
        # We keep it so __exit__ can close everything correctly later.
        self._session_context = get_session()

        # Enter the DB context manager to get a live SQLAlchemy session object.
        # A session is the main object used to query, insert, update, and delete rows.
        self.session = self._session_context.__enter__()

        # Create repository objects and inject the same session into both.
        # Repositories are responsible only for database access (SQL/ORM operations).
        customer_repo = CustomerRepository(self.session)
        order_repo = OrderRepository(self.session)
        sales_repo = SalesRepository(self.session)

        # Create service objects (business logic layer).
        # Services contain rules/validation and call repositories internally.
        # Important: both MCP tools and Streamlit UI use these same services,
        # so business logic is defined once and reused everywhere.
        self.customer_service = CustomerService(customer_repo, order_repo)
        self.order_service = OrderService(customer_repo, order_repo)
        self.analytics_service = AnalyticsService(customer_repo, order_repo, sales_repo)

        # Return self so caller can access factory.customer_service, factory.order_service, etc.
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # __exit__ runs automatically when the "with" block ends.
        # If code succeeded, the DB context commits.
        # If an error happened, it rolls back.
        # In all cases, it closes the session to avoid connection leaks.
        if self._session_context:
            self._session_context.__exit__(exc_type, exc, tb)


# These functions attach MCP capabilities to the server during startup.
# Tools: callable actions (can read/write data).
# Resources: read-only data endpoints.
# Prompts: reusable prompt templates for AI agent workflows.
# After registration, MCP clients can discover and call them.
register_tools(mcp, ServiceFactory)
register_resources(mcp, ServiceFactory)
register_prompts(mcp, ServiceFactory)
