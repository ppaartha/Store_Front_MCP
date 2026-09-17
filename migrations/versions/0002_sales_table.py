"""Add sales fact table for richer analytics.

Revision ID: 0002_sales_table
Revises: 0001_initial
Create Date: 2026-07-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_sales_table"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("gross_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("refund_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("cost_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("profit_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sale_date", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )

    op.create_index(op.f("ix_sales_id"), "sales", ["id"], unique=False)
    op.create_index(op.f("ix_sales_order_id"), "sales", ["order_id"], unique=True)
    op.create_index(op.f("ix_sales_customer_id"), "sales", ["customer_id"], unique=False)
    op.create_index(op.f("ix_sales_channel"), "sales", ["channel"], unique=False)
    op.create_index(op.f("ix_sales_region"), "sales", ["region"], unique=False)
    op.create_index(op.f("ix_sales_status"), "sales", ["status"], unique=False)
    op.create_index(op.f("ix_sales_sale_date"), "sales", ["sale_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_sale_date"), table_name="sales")
    op.drop_index(op.f("ix_sales_status"), table_name="sales")
    op.drop_index(op.f("ix_sales_region"), table_name="sales")
    op.drop_index(op.f("ix_sales_channel"), table_name="sales")
    op.drop_index(op.f("ix_sales_customer_id"), table_name="sales")
    op.drop_index(op.f("ix_sales_order_id"), table_name="sales")
    op.drop_index(op.f("ix_sales_id"), table_name="sales")
    op.drop_table("sales")
