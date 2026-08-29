"""Request schemas for purchase-order operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


Money = Annotated[Decimal, Field(ge=0, decimal_places=2)]


class OrderDetailInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    part_id: int = Field(alias="partId", gt=0)
    quantity: int = Field(gt=0)
    unit_price: Money = Field(alias="unitPrice")
    subtotal: Money | None = None
    remark: str | None = Field(default=None, max_length=200)


class OrderCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_number: str | None = Field(default=None, alias="orderNumber", max_length=50)
    total_amount: Money | None = Field(default=None, alias="totalAmount")
    status: int = Field(default=1, ge=1, le=5)
    order_time: datetime | None = Field(default=None, alias="orderTime")
    expected_delivery_date: date | None = Field(
        default=None, alias="expectedDeliveryDate"
    )
    actual_delivery_date: date | None = Field(
        default=None, alias="actualDeliveryDate"
    )
    created_by: int | None = Field(default=None, alias="createdBy", gt=0)
    remark: str | None = Field(default=None, max_length=500)
    order_detail: list[OrderDetailInput] = Field(alias="orderDetail", min_length=1)


class OrderUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_number: str | None = Field(default=None, alias="orderNumber", max_length=50)
    total_amount: Money | None = Field(default=None, alias="totalAmount")
    status: int | None = Field(default=None, ge=1, le=5)
    order_time: datetime | None = Field(default=None, alias="orderTime")
    expected_delivery_date: date | None = Field(
        default=None, alias="expectedDeliveryDate"
    )
    actual_delivery_date: date | None = Field(
        default=None, alias="actualDeliveryDate"
    )
    created_by: int | None = Field(default=None, alias="createdBy", gt=0)
    remark: str | None = Field(default=None, max_length=500)
    order_detail: list[OrderDetailInput] | None = Field(
        default=None, alias="orderDetail", min_length=1
    )

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one order field must be supplied")
        return self

