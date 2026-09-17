"""Business logic layer shared by MCP and Streamlit."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import ValidationError

from models import Customer, Order
from repositories import CustomerRepository, DuplicateEmailError, OrderRepository, SalesRepository
from schemas import CustomerCreate, CustomerRead, CustomerUpdate, DashboardSummary, OrderCreate, OrderRead


class NotFoundError(ValueError):
    """Raised when a requested entity does not exist."""


class ServiceValidationError(ValueError):
    """Raised for validation or user-input related failures."""


class CustomerService:
    """Business operations for customer management."""

    def __init__(self, customer_repo: CustomerRepository, order_repo: OrderRepository) -> None:
        self.customer_repo = customer_repo
        self.order_repo = order_repo

    def list_customers(self) -> list[CustomerRead]:
        return [CustomerRead.model_validate(c) for c in self.customer_repo.list_all()]

    def get_customer(self, customer_id: int) -> CustomerRead:
        customer = self.customer_repo.get_by_id(customer_id)
        if customer is None:
            raise NotFoundError(f"Customer with id={customer_id} not found")
        return CustomerRead.model_validate(customer)

    def search_customer(self, name: str) -> list[CustomerRead]:
        return [CustomerRead.model_validate(c) for c in self.customer_repo.search_by_name(name)]

    def search_customer_email(self, email: str) -> CustomerRead:
        customer = self.customer_repo.get_by_email(email)
        if customer is None:
            raise NotFoundError(f"Customer with email={email} not found")
        return CustomerRead.model_validate(customer)

    def create_customer(self, payload: dict) -> CustomerRead:
        try:
            data = CustomerCreate.model_validate(payload)
        except ValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc

        customer = Customer(**data.model_dump())
        try:
            created = self.customer_repo.create(customer)
        except DuplicateEmailError as exc:
            raise ServiceValidationError(str(exc)) from exc
        return CustomerRead.model_validate(created)

    def update_customer(self, customer_id: int, payload: dict) -> CustomerRead:
        customer = self.customer_repo.get_by_id(customer_id)
        if customer is None:
            raise NotFoundError(f"Customer with id={customer_id} not found")

        try:
            data = CustomerUpdate.model_validate(payload)
        except ValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc

        for key, value in data.model_dump(exclude_none=True).items():
            setattr(customer, key, value)

        try:
            updated = self.customer_repo.update(customer)
        except DuplicateEmailError as exc:
            raise ServiceValidationError(str(exc)) from exc

        return CustomerRead.model_validate(updated)

    def delete_customer(self, customer_id: int) -> dict:
        customer = self.customer_repo.get_by_id(customer_id)
        if customer is None:
            raise NotFoundError(f"Customer with id={customer_id} not found")
        self.customer_repo.delete(customer)
        return {"deleted": True, "customer_id": customer_id}

    def customers_by_country(self, country: str) -> list[CustomerRead]:
        return [CustomerRead.model_validate(c) for c in self.customer_repo.by_country(country)]

    def customers_by_status(self, status: str) -> list[CustomerRead]:
        if status not in {"active", "inactive"}:
            raise ServiceValidationError("Status must be 'active' or 'inactive'")
        return [CustomerRead.model_validate(c) for c in self.customer_repo.by_status(status)]

    def count_customers(self) -> int:
        return self.customer_repo.count()

    def list_countries(self) -> list[str]:
        return self.customer_repo.list_countries()


class OrderService:
    """Business operations for order management."""

    def __init__(self, customer_repo: CustomerRepository, order_repo: OrderRepository) -> None:
        self.customer_repo = customer_repo
        self.order_repo = order_repo

    def list_orders(self) -> list[OrderRead]:
        return [OrderRead.model_validate(o) for o in self.order_repo.list_all()]

    def get_order(self, order_id: int) -> OrderRead:
        order = self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order with id={order_id} not found")
        return OrderRead.model_validate(order)

    def customer_orders(self, customer_id: int) -> list[OrderRead]:
        if self.customer_repo.get_by_id(customer_id) is None:
            raise NotFoundError(f"Customer with id={customer_id} not found")
        return [OrderRead.model_validate(o) for o in self.order_repo.by_customer(customer_id)]

    def create_order(self, payload: dict) -> OrderRead:
        try:
            data = OrderCreate.model_validate(payload)
        except ValidationError as exc:
            raise ServiceValidationError(str(exc)) from exc

        customer = self.customer_repo.get_by_id(data.customer_id)
        if customer is None:
            raise NotFoundError(f"Customer with id={data.customer_id} not found")

        total_price = Decimal(data.quantity) * Decimal(data.unit_price)
        order = Order(
            customer_id=data.customer_id,
            product_name=data.product_name,
            quantity=data.quantity,
            unit_price=data.unit_price,
            total_price=total_price,
            order_date=datetime.now(timezone.utc),
        )
        created = self.order_repo.create(order)
        return OrderRead.model_validate(created)

    def delete_order(self, order_id: int) -> dict:
        order = self.order_repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Order with id={order_id} not found")
        self.order_repo.delete(order)
        return {"deleted": True, "order_id": order_id}

    def recent_orders(self, days: int = 30) -> list[OrderRead]:
        return [OrderRead.model_validate(o) for o in self.order_repo.recent(days=days)]

    def highest_order(self) -> OrderRead | None:
        order = self.order_repo.highest_order()
        if order is None:
            return None
        return OrderRead.model_validate(order)

    def calculate_customer_total(self, customer_id: int) -> Decimal:
        if self.customer_repo.get_by_id(customer_id) is None:
            raise NotFoundError(f"Customer with id={customer_id} not found")
        return self.order_repo.total_for_customer(customer_id)


class AnalyticsService:
    """Aggregates and dashboard-specific business analytics."""

    def __init__(
        self,
        customer_repo: CustomerRepository,
        order_repo: OrderRepository,
        sales_repo: SalesRepository,
    ) -> None:
        self.customer_repo = customer_repo
        self.order_repo = order_repo
        self.sales_repo = sales_repo

    def dashboard_summary(self) -> DashboardSummary:
        active_count = len(self.customer_repo.by_status("active"))
        inactive_count = len(self.customer_repo.by_status("inactive"))
        return DashboardSummary(
            total_customers=self.customer_repo.count(),
            total_orders=self.order_repo.count(),
            revenue=self.order_repo.revenue(),
            active_customers=active_count,
            inactive_customers=inactive_count,
        )

    def revenue_by_country(self) -> list[dict]:
        return self.order_repo.revenue_by_country()

    def revenue_by_customer(self) -> list[dict]:
        return self.order_repo.revenue_by_customer()

    def orders_per_customer(self) -> list[dict]:
        return self.order_repo.orders_per_customer()

    def sales_summary(self) -> dict:
        totals = self.sales_repo.revenue_totals()
        sales_count = self.sales_repo.count()
        aov = self.sales_repo.average_order_value() if sales_count > 0 else Decimal(0)

        margin_pct = Decimal(0)
        if totals["net"] > 0:
            margin_pct = (totals["profit"] / totals["net"]) * Decimal(100)

        return {
            "sales_count": sales_count,
            "gross_revenue": totals["gross"],
            "discount_total": totals["discount"],
            "refund_total": totals["refund"],
            "net_revenue": totals["net"],
            "total_cost": totals["cost"],
            "total_profit": totals["profit"],
            "profit_margin_pct": margin_pct.quantize(Decimal("0.01")),
            "average_order_value": aov.quantize(Decimal("0.01")),
        }

    def generate_sales_insights(self) -> dict:
        """Generate a standard sales report from sales fact data.

        This report intentionally uses a fixed default scope so the AI assistant can
        answer generic requests like "generate sales insights" without requiring
        additional parameters.
        """
        summary = self.sales_summary()
        top_products = self.sales_repo.top_products(limit=5)
        top_regions = self.sales_repo.top_regions(limit=5)
        channels = self.sales_repo.channel_mix()
        trend = self.sales_repo.monthly_trend(months=6)

        highlights: list[str] = []
        if top_products:
            best = top_products[0]
            highlights.append(
                f"Top product: {best['product_name']} with revenue {best['revenue']}."
            )
        if top_regions:
            best_region = top_regions[0]
            highlights.append(
                f"Strongest region: {best_region['region']} with revenue {best_region['revenue']}."
            )
        if channels:
            best_channel = channels[0]
            highlights.append(
                f"Best channel: {best_channel['channel']} with revenue {best_channel['revenue']}."
            )
        if not highlights:
            highlights.append("No sales data available yet. Seed or ingest sales facts first.")

        return {
            "scope": "standard_default_report",
            "summary": summary,
            "monthly_trend": trend,
            "top_products": top_products,
            "top_regions": top_regions,
            "channel_mix": channels,
            "highlights": highlights,
        }
