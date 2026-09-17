"""MCP resources offering read-only data snapshots for agents."""

from decimal import Decimal


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def register_resources(mcp, service_factory_cls) -> None:
    """Register all required MCP resources."""

    @mcp.resource("customer://all")
    def customer_all() -> list[dict]:
        with service_factory_cls() as factory:
            return [item.model_dump(mode="json") for item in factory.customer_service.list_customers()]

    @mcp.resource("customer://active")
    def customer_active() -> list[dict]:
        with service_factory_cls() as factory:
            return [
                item.model_dump(mode="json")
                for item in factory.customer_service.customers_by_status("active")
            ]

    @mcp.resource("customer://countries")
    def customer_countries() -> list[str]:
        with service_factory_cls() as factory:
            return factory.customer_service.list_countries()

    @mcp.resource("customer://schema")
    def customer_schema() -> dict:
        return {
            "table": "customers",
            "fields": [
                "id",
                "name",
                "email",
                "phone",
                "city",
                "country",
                "status",
                "created_at",
            ],
        }

    @mcp.resource("orders://all")
    def orders_all() -> list[dict]:
        with service_factory_cls() as factory:
            return [item.model_dump(mode="json") for item in factory.order_service.list_orders()]

    @mcp.resource("orders://recent")
    def orders_recent() -> list[dict]:
        with service_factory_cls() as factory:
            return [item.model_dump(mode="json") for item in factory.order_service.recent_orders(30)]

    @mcp.resource("orders://summary")
    def orders_summary() -> dict:
        with service_factory_cls() as factory:
            summary = factory.analytics_service.dashboard_summary()
            highest = factory.order_service.highest_order()
            return {
                "total_orders": summary.total_orders,
                "revenue": str(summary.revenue),
                "highest_order": highest.model_dump(mode="json") if highest else None,
            }

    @mcp.resource("sales://all")
    def sales_all() -> list[dict]:
        with service_factory_cls() as factory:
            rows = factory.analytics_service.sales_repo.list_all()
            return [
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

    @mcp.resource("sales://summary")
    def sales_summary() -> dict:
        with service_factory_cls() as factory:
            summary = factory.analytics_service.sales_summary()
            insights = factory.analytics_service.generate_sales_insights()
            return {
                "summary": summary,
                "highlights": insights["highlights"],
                "top_products": insights["top_products"],
                "top_regions": insights["top_regions"],
            }
