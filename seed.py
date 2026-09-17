"""Database seeding utilities for classroom-ready demo data."""

from __future__ import annotations

import argparse
import random
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy import select

from database import run_migrations
from models import Customer, Order, Sales
from server import ServiceFactory


def _customer_seed_data() -> list[dict[str, str]]:
    """Return deterministic customer seed records."""
    return [
        {"name": "Ava Johnson", "email": "ava.johnson@example.com", "phone": "+1-415-555-1001", "city": "San Francisco", "country": "USA", "status": "active"},
        {"name": "Liam Smith", "email": "liam.smith@example.com", "phone": "+1-212-555-1002", "city": "New York", "country": "USA", "status": "active"},
        {"name": "Noah Brown", "email": "noah.brown@example.com", "phone": "+44-20-5555-1003", "city": "London", "country": "UK", "status": "inactive"},
        {"name": "Emma Davis", "email": "emma.davis@example.com", "phone": "+49-30-5555-1004", "city": "Berlin", "country": "Germany", "status": "active"},
        {"name": "Olivia Wilson", "email": "olivia.wilson@example.com", "phone": "+33-1-5555-1005", "city": "Paris", "country": "France", "status": "active"},
        {"name": "Elijah Moore", "email": "elijah.moore@example.com", "phone": "+91-80-5555-1006", "city": "Bengaluru", "country": "India", "status": "active"},
        {"name": "Sophia Taylor", "email": "sophia.taylor@example.com", "phone": "+81-3-5555-1007", "city": "Tokyo", "country": "Japan", "status": "inactive"},
        {"name": "James Anderson", "email": "james.anderson@example.com", "phone": "+61-2-5555-1008", "city": "Sydney", "country": "Australia", "status": "active"},
        {"name": "Mia Thomas", "email": "mia.thomas@example.com", "phone": "+971-4-555-1009", "city": "Dubai", "country": "UAE", "status": "active"},
        {"name": "Benjamin Martin", "email": "ben.martin@example.com", "phone": "+65-6-555-1010", "city": "Singapore", "country": "Singapore", "status": "active"},
        {"name": "Charlotte Lee", "email": "charlotte.lee@example.com", "phone": "+1-647-555-1011", "city": "Toronto", "country": "Canada", "status": "inactive"},
        {"name": "Lucas Clark", "email": "lucas.clark@example.com", "phone": "+55-11-5555-1012", "city": "Sao Paulo", "country": "Brazil", "status": "active"},
        {"name": "Amelia Lewis", "email": "amelia.lewis@example.com", "phone": "+34-91-555-1013", "city": "Madrid", "country": "Spain", "status": "active"},
        {"name": "Henry Walker", "email": "henry.walker@example.com", "phone": "+39-06-555-1014", "city": "Rome", "country": "Italy", "status": "inactive"},
        {"name": "Harper Hall", "email": "harper.hall@example.com", "phone": "+31-20-555-1015", "city": "Amsterdam", "country": "Netherlands", "status": "active"},
        {"name": "Alexander Allen", "email": "alexander.allen@example.com", "phone": "+46-8-555-1016", "city": "Stockholm", "country": "Sweden", "status": "active"},
        {"name": "Evelyn Young", "email": "evelyn.young@example.com", "phone": "+82-2-555-1017", "city": "Seoul", "country": "South Korea", "status": "active"},
        {"name": "Daniel King", "email": "daniel.king@example.com", "phone": "+86-10-555-1018", "city": "Beijing", "country": "China", "status": "inactive"},
        {"name": "Abigail Scott", "email": "abigail.scott@example.com", "phone": "+52-55-555-1019", "city": "Mexico City", "country": "Mexico", "status": "active"},
        {"name": "Michael Green", "email": "michael.green@example.com", "phone": "+27-11-555-1020", "city": "Johannesburg", "country": "South Africa", "status": "active"},
    ]


def seed_data(force_reseed: bool = False) -> None:
    """Populate the database with 20 customers and 1-5 orders per customer."""
    random.seed(42)

    products = [
        "Laptop Pro 14",
        "Wireless Mouse",
        "USB-C Dock",
        "4K Monitor",
        "Mechanical Keyboard",
        "Noise Cancelling Headphones",
        "Cloud Subscription",
        "Office Chair",
        "Webcam HD",
        "External SSD",
    ]

    with ServiceFactory() as factory:
        current_count = factory.customer_service.count_customers()

        if current_count > 0 and not force_reseed:
            _backfill_sales_rows(factory)
            return

        if force_reseed and current_count > 0:
            factory.session.execute(delete(Sales))
            factory.session.execute(delete(Order))
            factory.session.execute(delete(Customer))

        for customer in _customer_seed_data():
            factory.customer_service.create_customer(customer)

        customers = factory.customer_service.list_customers()
        for customer in customers:
            order_count = random.randint(1, 5)
            for _ in range(order_count):
                quantity = random.randint(1, 8)
                unit_price = Decimal(str(round(random.uniform(20.0, 1500.0), 2)))
                factory.order_service.create_order(
                    {
                        "customer_id": customer.id,
                        "product_name": random.choice(products),
                        "quantity": quantity,
                        "unit_price": unit_price,
                    }
                )

        _backfill_sales_rows(factory)


def _backfill_sales_rows(factory) -> None:
    """Create one sales fact per order when missing.

    This keeps analytics data available even if the schema is upgraded on an
    existing classroom database that already contains orders.
    """
    channels = ["web", "mobile", "partner", "retail"]

    existing_order_ids = set(factory.session.scalars(select(Sales.order_id)).all())
    orders = factory.order_service.list_orders()
    customers = {c.id: c for c in factory.customer_service.list_customers()}

    for order in orders:
        if order.id in existing_order_ids:
            continue

        gross = Decimal(order.total_price)
        discount = (gross * Decimal(str(round(random.uniform(0.0, 0.15), 2)))).quantize(Decimal("0.01"))

        status_roll = random.random()
        if status_roll < 0.12:
            status = "refunded"
            refund = (gross - discount).quantize(Decimal("0.01"))
        elif status_roll < 0.20:
            status = "pending"
            refund = Decimal("0.00")
        else:
            status = "completed"
            refund = Decimal("0.00")

        net = (gross - discount - refund).quantize(Decimal("0.01"))
        cost = (max(net, Decimal("0.00")) * Decimal(str(round(random.uniform(0.45, 0.80), 2)))).quantize(
            Decimal("0.01")
        )
        profit = (net - cost).quantize(Decimal("0.01"))

        customer = customers.get(order.customer_id)
        region = customer.country if customer else "Unknown"

        factory.analytics_service.sales_repo.create(
            Sales(
                order_id=order.id,
                customer_id=order.customer_id,
                product_name=order.product_name,
                quantity=order.quantity,
                channel=random.choice(channels),
                region=region,
                currency="USD",
                status=status,
                gross_amount=gross,
                discount_amount=discount,
                refund_amount=refund,
                net_amount=net,
                cost_amount=cost,
                profit_amount=profit,
                sale_date=order.order_date,
            )
        )


def bootstrap(migrate: bool = True, force_reseed: bool = False) -> None:
    """Initialize schema and seed records for local/dev/demo environments."""
    if migrate:
        run_migrations()
    seed_data(force_reseed=force_reseed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run migrations and seed sample data")
    parser.add_argument("--migrate", action="store_true", help="Run Alembic migrations before seeding")
    parser.add_argument("--force-reseed", action="store_true", help="Delete all data then reseed")
    args = parser.parse_args()

    bootstrap(migrate=args.migrate, force_reseed=args.force_reseed)


if __name__ == "__main__":
    main()
