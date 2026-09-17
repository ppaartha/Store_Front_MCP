"""MCP tools exposing customer and order operations."""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from services import NotFoundError, ServiceValidationError

logger = logging.getLogger("mcp.requests")


def _serialize_model(value: Any) -> Any:
    """Convert Pydantic models and nested lists into plain JSON-friendly data.

    MCP clients expect simple JSON-like responses. This helper makes sure we do not
    leak raw ORM objects or Pydantic instances back to the client.
    """
    if isinstance(value, list):
        # If the result is a list, convert each item one by one.
        return [_serialize_model(item) for item in value]
    if hasattr(value, "model_dump"):
        # Pydantic models can serialize themselves into standard Python dictionaries.
        return value.model_dump(mode="json")
    # Plain values such as numbers, strings, dictionaries, and booleans pass through.
    return value


def log_mcp_request(tool_name: str) -> Callable:
    """Decorator to provide teaching-friendly request logs for every MCP tool call.

    A decorator is a wrapper around a function. Here it adds logging before returning
    the result, so every MCP tool call gets consistent telemetry without repeating code
    in each tool function.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Start a timer so we can measure how long the tool call took.
            start_time = time.perf_counter()
            try:
                # Run the actual MCP tool logic.
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                # Log a success entry with timestamp, tool name, arguments, and duration.
                logger.info(
                    "timestamp=%s tool=%s args=%s execution_ms=%.2f success=true",
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    tool_name,
                    kwargs,
                    elapsed_ms,
                )
                return result
            except Exception as exc:
                # If the tool fails, we still log the request so students can debug it.
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "timestamp=%s tool=%s args=%s execution_ms=%.2f success=false error=%s",
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    tool_name,
                    kwargs,
                    elapsed_ms,
                    str(exc),
                )
                raise

        return wrapper

    return decorator


def _handle_service_errors(exc: Exception) -> None:
    """Convert domain exceptions into user-facing MCP errors.

    The service layer raises domain-specific exceptions like validation problems or
    missing records. This helper turns those into a simple error that MCP clients can
    display cleanly.
    """
    if isinstance(exc, (ServiceValidationError, NotFoundError, ValueError)):
        # These are expected problems caused by input or missing data.
        raise ValueError(str(exc)) from exc
    # Anything else is unexpected and should be surfaced as a server-side failure.
    raise RuntimeError(f"Unexpected server error: {exc}") from exc


def register_tools(mcp, service_factory_cls) -> None:
    """Register all required MCP tools.

    This function connects the business logic layer to the MCP server. Each inner
    function becomes a tool that an MCP client can call directly.
    """

    # -------------------------
    # Customer tools
    # -------------------------

    @mcp.tool(name="search_customer")
    @log_mcp_request("search_customer")
    def search_customer(name: str) -> dict:
        # Search customers by partial name match.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.search_customer(name)
            return {"customers": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="get_customer")
    @log_mcp_request("get_customer")
    def get_customer(customer_id: int) -> dict:
        # Fetch one customer by ID.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.get_customer(customer_id)
            return _serialize_model(result)
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="create_customer")
    @log_mcp_request("create_customer")
    def create_customer(name: str, email: str, phone: str, city: str, country: str, status: str = "active") -> dict:
        # Create a new customer record from the provided fields.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.create_customer(
                    {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "city": city,
                        "country": country,
                        "status": status,
                    }
                )
            return _serialize_model(result)
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="update_customer")
    @log_mcp_request("update_customer")
    def update_customer(customer_id: int, updates: dict) -> dict:
        # Apply only the provided fields to an existing customer.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.update_customer(customer_id, updates)
            return _serialize_model(result)
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="delete_customer")
    @log_mcp_request("delete_customer")
    def delete_customer(customer_id: int) -> dict:
        # Remove a customer from the database.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.delete_customer(customer_id)
            return result
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="list_customers")
    @log_mcp_request("list_customers")
    def list_customers() -> dict:
        # Return every customer so the client can render a table.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.list_customers()
            return {"customers": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="customers_by_country")
    @log_mcp_request("customers_by_country")
    def customers_by_country(country: str) -> dict:
        # Group customers by the country field for demos and analytics.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.customers_by_country(country)
            return {"customers": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="customers_by_status")
    @log_mcp_request("customers_by_status")
    def customers_by_status(status: str) -> dict:
        # Filter customers into active or inactive groups.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.customers_by_status(status)
            return {"customers": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="count_customers")
    @log_mcp_request("count_customers")
    def count_customers() -> dict:
        # Return a single numeric summary instead of a list.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.count_customers()
            return {"count": result}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="search_customer_email")
    @log_mcp_request("search_customer_email")
    def search_customer_email(email: str) -> dict:
        # Look up a customer using the email address, which should be unique.
        try:
            with service_factory_cls() as factory:
                result = factory.customer_service.search_customer_email(email)
            return _serialize_model(result)
        except Exception as exc:
            _handle_service_errors(exc)

    # -------------------------
    # Order tools
    # -------------------------

    @mcp.tool(name="list_orders")
    @log_mcp_request("list_orders")
    def list_orders() -> dict:
        # Return all orders in the system.
        try:
            with service_factory_cls() as factory:
                result = factory.order_service.list_orders()
            return {"orders": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="get_order")
    @log_mcp_request("get_order")
    def get_order(order_id: int) -> dict:
        # Fetch one order by its ID.
        try:
            with service_factory_cls() as factory:
                result = factory.order_service.get_order(order_id)
            return _serialize_model(result)
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="customer_orders")
    @log_mcp_request("customer_orders")
    def customer_orders(customer_id: int) -> dict:
        # Show only the orders that belong to one customer.
        try:
            with service_factory_cls() as factory:
                result = factory.order_service.customer_orders(customer_id)
            return {"orders": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="create_order")
    @log_mcp_request("create_order")
    def create_order(customer_id: int, product_name: str, quantity: int, unit_price: float) -> dict:
        # Create a new order and let the service layer calculate total_price.
        try:
            with service_factory_cls() as factory:
                result = factory.order_service.create_order(
                    {
                        "customer_id": customer_id,
                        "product_name": product_name,
                        "quantity": quantity,
                        "unit_price": unit_price,
                    }
                )
            return _serialize_model(result)
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="delete_order")
    @log_mcp_request("delete_order")
    def delete_order(order_id: int) -> dict:
        # Remove an order by ID.
        try:
            with service_factory_cls() as factory:
                result = factory.order_service.delete_order(order_id)
            return result
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="recent_orders")
    @log_mcp_request("recent_orders")
    def recent_orders(days: int = 30) -> dict:
        # Return orders from the last N days for recent activity demos.
        try:
            with service_factory_cls() as factory:
                result = factory.order_service.recent_orders(days)
            return {"orders": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="highest_order")
    @log_mcp_request("highest_order")
    def highest_order() -> dict:
        # Return the largest single order by total value.
        try:
            with service_factory_cls() as factory:
                result = factory.order_service.highest_order()
            return {"order": _serialize_model(result)}
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="calculate_customer_total")
    @log_mcp_request("calculate_customer_total")
    def calculate_customer_total(customer_id: int) -> dict:
        # Sum all orders for one customer to show customer lifetime value.
        try:
            with service_factory_cls() as factory:
                total = factory.order_service.calculate_customer_total(customer_id)
            return {"customer_id": customer_id, "total": str(total)}
        except Exception as exc:
            _handle_service_errors(exc)

    # -------------------------
    # Sales insight tools
    # -------------------------

    @mcp.tool(name="list_sales")
    @log_mcp_request("list_sales")
    def list_sales() -> dict:
        # Return all sales fact rows for analytics and reporting.
        try:
            with service_factory_cls() as factory:
                rows = factory.analytics_service.sales_repo.list_all()
            return {
                "sales": [
                    {
                        "id": item.id,
                        "order_id": item.order_id,
                        "customer_id": item.customer_id,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "channel": item.channel,
                        "region": item.region,
                        "currency": item.currency,
                        "status": item.status,
                        "gross_amount": str(item.gross_amount),
                        "discount_amount": str(item.discount_amount),
                        "refund_amount": str(item.refund_amount),
                        "net_amount": str(item.net_amount),
                        "cost_amount": str(item.cost_amount),
                        "profit_amount": str(item.profit_amount),
                        "sale_date": item.sale_date.isoformat(),
                    }
                    for item in rows
                ]
            }
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="sales_summary")
    @log_mcp_request("sales_summary")
    def sales_summary() -> dict:
        # Return high-level sales metrics (gross/net/profit/AOV/margin).
        try:
            with service_factory_cls() as factory:
                summary = factory.analytics_service.sales_summary()
            return _serialize_model(summary)
        except Exception as exc:
            _handle_service_errors(exc)

    @mcp.tool(name="generate_sales_insights")
    @log_mcp_request("generate_sales_insights")
    def generate_sales_insights() -> dict:
        # Produce a standard default sales report for generic insight requests.
        try:
            with service_factory_cls() as factory:
                insights = factory.analytics_service.generate_sales_insights()
            return _serialize_model(insights)
        except Exception as exc:
            _handle_service_errors(exc)
