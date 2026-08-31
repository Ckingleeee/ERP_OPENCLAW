"""Request schemas for marketing-resource replenishment operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


Money = Annotated[Decimal, Field(ge=0, decimal_places=2)]


class ReplenishmentDetailInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resource_id: int = Field(alias="resourceId", gt=0)
    quantity: int = Field(gt=0)
    unit_cost: Money = Field(alias="unitCost")
    subtotal: Money | None = None
    remark: str | None = Field(default=None, max_length=200)


class ReplenishmentCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    replenishment_number: str | None = Field(
        default=None, alias="replenishmentNumber", max_length=50
    )
    total_amount: Money | None = Field(default=None, alias="totalAmount")
    status: int = Field(default=1, ge=1, le=5)
    replenishment_time: datetime | None = Field(
        default=None, alias="replenishmentTime"
    )
    expected_activation_date: date | None = Field(
        default=None, alias="expectedActivationDate"
    )
    actual_activation_date: date | None = Field(
        default=None, alias="actualActivationDate"
    )
    created_by: int | None = Field(default=None, alias="createdBy", gt=0)
    remark: str | None = Field(default=None, max_length=500)
    detail: list[ReplenishmentDetailInput] = Field(min_length=1)


class ReplenishmentUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    replenishment_number: str | None = Field(
        default=None, alias="replenishmentNumber", max_length=50
    )
    total_amount: Money | None = Field(default=None, alias="totalAmount")
    status: int | None = Field(default=None, ge=1, le=5)
    replenishment_time: datetime | None = Field(
        default=None, alias="replenishmentTime"
    )
    expected_activation_date: date | None = Field(
        default=None, alias="expectedActivationDate"
    )
    actual_activation_date: date | None = Field(
        default=None, alias="actualActivationDate"
    )
    created_by: int | None = Field(default=None, alias="createdBy", gt=0)
    remark: str | None = Field(default=None, max_length=500)
    detail: list[ReplenishmentDetailInput] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one replenishment field must be supplied")
        return self
