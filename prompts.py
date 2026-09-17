"""MCP prompts that help agents compose useful responses."""


def register_prompts(mcp, service_factory_cls) -> None:
    """Register all required MCP prompts."""

    @mcp.prompt(name="Customer Summary")
    def customer_summary(customer_id: int) -> str:
        with service_factory_cls() as factory:
            customer = factory.customer_service.get_customer(customer_id)
            total = factory.order_service.calculate_customer_total(customer_id)
            orders = factory.order_service.customer_orders(customer_id)
        return (
            "Create a concise customer summary using this data:\n"
            f"Customer: {customer.model_dump(mode='json')}\n"
            f"Order count: {len(orders)}\n"
            f"Total spend: {total}\n"
            "Explain the customer value in 5 bullet points."
        )

    @mcp.prompt(name="Sales Summary")
    def sales_summary() -> str:
        with service_factory_cls() as factory:
            summary = factory.analytics_service.sales_summary()
            insights = factory.analytics_service.generate_sales_insights()
        return (
            "Create a classroom-friendly sales summary using the sales fact table.\n"
            f"Sales summary: {summary}\n"
            f"Top products: {insights['top_products']}\n"
            f"Top regions: {insights['top_regions']}\n"
            f"Channel mix: {insights['channel_mix']}\n"
            "Highlight trends, one risk, and one recommendation."
        )

    @mcp.prompt(name="Inactive Customer Report")
    def inactive_customer_report() -> str:
        with service_factory_cls() as factory:
            inactive = factory.customer_service.customers_by_status("inactive")
        return (
            "Generate an inactive customer reactivation report from this data:\n"
            f"Inactive customers: {[c.model_dump(mode='json') for c in inactive]}\n"
            "Include likely reasons and recovery actions."
        )

    @mcp.prompt(name="Customer Lookup Assistant")
    def customer_lookup_assistant(query: str) -> str:
        return (
            "You are an assistant helping locate customer records.\n"
            f"User query: {query}\n"
            "Recommend the best tool to call first, then fallback tools if no result."
        )

    @mcp.prompt(name="Generate Customer Email")
    def generate_customer_email(customer_id: int, purpose: str) -> str:
        with service_factory_cls() as factory:
            customer = factory.customer_service.get_customer(customer_id)
        return (
            "Write a professional customer email.\n"
            f"Customer data: {customer.model_dump(mode='json')}\n"
            f"Purpose: {purpose}\n"
            "Tone: friendly and concise."
        )

    @mcp.prompt(name="Generate Sales Insights")
    def generate_sales_insights() -> str:
        with service_factory_cls() as factory:
            report = factory.analytics_service.generate_sales_insights()
        return (
            "Generate 6 practical sales insights for a teaching demo using:\n"
            f"Summary: {report['summary']}\n"
            f"Monthly trend: {report['monthly_trend']}\n"
            f"Top products: {report['top_products']}\n"
            f"Top regions: {report['top_regions']}\n"
            f"Channel mix: {report['channel_mix']}"
        )
