"""Repository layer encapsulating all database queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Customer, Order, Sales


class DuplicateEmailError(ValueError):
    """Raised when an email already exists in the customers table."""


class CustomerRepository:
    """Customer data access operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Customer]:
        return list(self.session.scalars(select(Customer).order_by(Customer.id)).all())

    def get_by_id(self, customer_id: int) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def get_by_email(self, email: str) -> Customer | None:
        return self.session.scalar(select(Customer).where(Customer.email == email))

    def search_by_name(self, name: str) -> list[Customer]:
        stmt = select(Customer).where(Customer.name.ilike(f"%{name}%")).order_by(Customer.name)
        return list(self.session.scalars(stmt).all())

    def by_country(self, country: str) -> list[Customer]:
        stmt = select(Customer).where(Customer.country.ilike(country)).order_by(Customer.name)
        return list(self.session.scalars(stmt).all())

    def by_status(self, status: str) -> list[Customer]:
        stmt = select(Customer).where(Customer.status == status).order_by(Customer.name)
        return list(self.session.scalars(stmt).all())

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(Customer)) or 0)

    def list_countries(self) -> list[str]:
        stmt = select(Customer.country).distinct().order_by(Customer.country)
        return [row for row in self.session.scalars(stmt).all()]

    def create(self, customer: Customer) -> Customer:
        self.session.add(customer)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateEmailError("A customer with this email already exists") from exc
        self.session.refresh(customer)
        return customer

    def update(self, customer: Customer) -> Customer:
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DuplicateEmailError("A customer with this email already exists") from exc
        self.session.refresh(customer)
        return customer

    def delete(self, customer: Customer) -> None:
        self.session.delete(customer)
        self.session.flush()


class OrderRepository:
    """Order data access operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Order]:
        return list(self.session.scalars(select(Order).order_by(Order.id)).all())

    def get_by_id(self, order_id: int) -> Order | None:
        return self.session.get(Order, order_id)

    def by_customer(self, customer_id: int) -> list[Order]:
        stmt = select(Order).where(Order.customer_id == customer_id).order_by(Order.order_date.desc())
        return list(self.session.scalars(stmt).all())

    def create(self, order: Order) -> Order:
        self.session.add(order)
        self.session.flush()
        self.session.refresh(order)
        return order

    def delete(self, order: Order) -> None:
        self.session.delete(order)
        self.session.flush()

    def recent(self, days: int = 30) -> list[Order]:
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = select(Order).where(Order.order_date >= start_date).order_by(Order.order_date.desc())
        return list(self.session.scalars(stmt).all())

    def highest_order(self) -> Order | None:
        stmt = select(Order).order_by(Order.total_price.desc()).limit(1)
        return self.session.scalar(stmt)

    def total_for_customer(self, customer_id: int) -> Decimal:
        total = self.session.scalar(
            select(func.coalesce(func.sum(Order.total_price), 0)).where(Order.customer_id == customer_id)
        )
        return Decimal(total)

    def revenue(self) -> Decimal:
        total = self.session.scalar(select(func.coalesce(func.sum(Order.total_price), 0)).select_from(Order))
        return Decimal(total)

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(Order)) or 0)

    def revenue_by_country(self) -> list[dict[str, Decimal | str]]:
        stmt = (
            select(Customer.country, func.coalesce(func.sum(Order.total_price), 0))
            .join(Order, Customer.id == Order.customer_id)
            .group_by(Customer.country)
            .order_by(func.sum(Order.total_price).desc())
        )
        return [
            {"country": country, "revenue": Decimal(revenue)}
            for country, revenue in self.session.execute(stmt).all()
        ]

    def revenue_by_customer(self) -> list[dict[str, Decimal | str | int]]:
        stmt = (
            select(Customer.id, Customer.name, func.coalesce(func.sum(Order.total_price), 0))
            .join(Order, Customer.id == Order.customer_id)
            .group_by(Customer.id, Customer.name)
            .order_by(func.sum(Order.total_price).desc())
        )
        return [
            {"customer_id": customer_id, "name": name, "revenue": Decimal(revenue)}
            for customer_id, name, revenue in self.session.execute(stmt).all()
        ]

    def orders_per_customer(self) -> list[dict[str, int | str]]:
        stmt = (
            select(Customer.id, Customer.name, func.count(Order.id))
            .join(Order, Customer.id == Order.customer_id)
            .group_by(Customer.id, Customer.name)
            .order_by(func.count(Order.id).desc())
        )
        return [
            {"customer_id": customer_id, "name": name, "order_count": int(order_count)}
            for customer_id, name, order_count in self.session.execute(stmt).all()
        ]


class SalesRepository:
    """Sales-fact data access operations for advanced analytics."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Sales]:
        stmt = select(Sales).order_by(Sales.sale_date.desc(), Sales.id.desc())
        return list(self.session.scalars(stmt).all())

    def count(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(Sales)) or 0)

    def order_ids_with_sales(self) -> set[int]:
        return set(self.session.scalars(select(Sales.order_id)).all())

    def create(self, sale: Sales) -> Sales:
        self.session.add(sale)
        self.session.flush()
        self.session.refresh(sale)
        return sale

    def revenue_totals(self) -> dict[str, Decimal]:
        gross = self.session.scalar(select(func.coalesce(func.sum(Sales.gross_amount), 0)).select_from(Sales))
        discount = self.session.scalar(select(func.coalesce(func.sum(Sales.discount_amount), 0)).select_from(Sales))
        refund = self.session.scalar(select(func.coalesce(func.sum(Sales.refund_amount), 0)).select_from(Sales))
        net = self.session.scalar(select(func.coalesce(func.sum(Sales.net_amount), 0)).select_from(Sales))
        cost = self.session.scalar(select(func.coalesce(func.sum(Sales.cost_amount), 0)).select_from(Sales))
        profit = self.session.scalar(select(func.coalesce(func.sum(Sales.profit_amount), 0)).select_from(Sales))
        return {
            "gross": Decimal(gross),
            "discount": Decimal(discount),
            "refund": Decimal(refund),
            "net": Decimal(net),
            "cost": Decimal(cost),
            "profit": Decimal(profit),
        }

    def average_order_value(self) -> Decimal:
        value = self.session.scalar(select(func.coalesce(func.avg(Sales.net_amount), 0)).select_from(Sales))
        return Decimal(value)

    def top_products(self, limit: int = 5) -> list[dict[str, Decimal | str | int]]:
        stmt = (
            select(
                Sales.product_name,
                func.count(Sales.id),
                func.coalesce(func.sum(Sales.net_amount), 0),
                func.coalesce(func.sum(Sales.profit_amount), 0),
            )
            .group_by(Sales.product_name)
            .order_by(func.sum(Sales.net_amount).desc())
            .limit(limit)
        )
        return [
            {
                "product_name": product_name,
                "order_count": int(order_count),
                "revenue": Decimal(revenue),
                "profit": Decimal(profit),
            }
            for product_name, order_count, revenue, profit in self.session.execute(stmt).all()
        ]

    def top_regions(self, limit: int = 5) -> list[dict[str, Decimal | str]]:
        stmt = (
            select(Sales.region, func.coalesce(func.sum(Sales.net_amount), 0))
            .group_by(Sales.region)
            .order_by(func.sum(Sales.net_amount).desc())
            .limit(limit)
        )
        return [
            {"region": region, "revenue": Decimal(revenue)}
            for region, revenue in self.session.execute(stmt).all()
        ]

    def channel_mix(self) -> list[dict[str, Decimal | str | int]]:
        stmt = (
            select(Sales.channel, func.count(Sales.id), func.coalesce(func.sum(Sales.net_amount), 0))
            .group_by(Sales.channel)
            .order_by(func.sum(Sales.net_amount).desc())
        )
        return [
            {"channel": channel, "order_count": int(order_count), "revenue": Decimal(revenue)}
            for channel, order_count, revenue in self.session.execute(stmt).all()
        ]

    def monthly_trend(self, months: int = 6) -> list[dict[str, Decimal | str | int]]:
        month_expr = func.date_trunc("month", Sales.sale_date)
        stmt = (
            select(month_expr, func.count(Sales.id), func.coalesce(func.sum(Sales.net_amount), 0))
            .group_by(month_expr)
            .order_by(month_expr.desc())
            .limit(months)
        )
        rows = self.session.execute(stmt).all()
        return [
            {
                "month": month.isoformat() if hasattr(month, "isoformat") else str(month),
                "order_count": int(order_count),
                "revenue": Decimal(revenue),
            }
            for month, order_count, revenue in reversed(rows)
        ]
