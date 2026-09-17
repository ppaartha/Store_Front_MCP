"""Pydantic schemas for validation and API contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerBase(BaseModel):
    """Shared customer fields with validation rules."""

    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    city: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=100)
    status: Literal["active", "inactive"] = "active"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = value.replace(" ", "").replace("-", "")
        if not cleaned.lstrip("+").isdigit():
            raise ValueError("Phone must contain digits and optional leading +")
        return value


class CustomerCreate(CustomerBase):
    """Payload for creating a customer."""


class CustomerUpdate(BaseModel):
    """Payload for updating a customer."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    status: Literal["active", "inactive"] | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.replace(" ", "").replace("-", "")
        if not cleaned.lstrip("+").isdigit():
            raise ValueError("Phone must contain digits and optional leading +")
        return value


class CustomerRead(CustomerBase):
    """Customer response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class OrderBase(BaseModel):
    """Shared order fields with validation."""

    customer_id: int = Field(gt=0)
    product_name: str = Field(min_length=2, max_length=200)
    quantity: int = Field(gt=0, le=10000)
    unit_price: Decimal = Field(gt=0)


class OrderCreate(OrderBase):
    """Payload for creating an order."""


class OrderRead(BaseModel):
    """Order response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    order_date: datetime


class DashboardSummary(BaseModel):
    """UI and analytics aggregate summary."""

    total_customers: int
    total_orders: int
    revenue: Decimal
    active_customers: int
    inactive_customers: int
