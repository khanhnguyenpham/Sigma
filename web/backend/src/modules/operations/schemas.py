from datetime import date
from pydantic import Field, field_validator, model_validator
from core.schemas import DTO
from typing import Literal

MAX_QTY = 2**53 - 1  # Exact JSON integer arithmetic in the React client.


class OpsWarehouseInput(DTO):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
    name: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=100)

    @field_validator("code", "name", "country")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("Field is required")
        return value.strip()


class OpsWarehouseUpdate(DTO):
    name: str = Field(min_length=1, max_length=120)
    country: str = Field(min_length=1, max_length=100)
    active: bool
    expected_version: int = Field(ge=1, strict=True)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("name", "country", "reason")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("Field is required")
        return value.strip()


class OpsProductInput(DTO):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=120)
    product_type: Literal["eSIM", "physical_SIM"]
    carrier: str = Field(min_length=1, max_length=100)
    destination_country: str = Field(min_length=1, max_length=100)

    @field_validator("name", "sku", "carrier", "destination_country")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("Field is required")
        return value.strip()


class OpsProductUpdate(DTO):
    name: str = Field(min_length=1, max_length=160)
    active: bool
    expected_version: int = Field(ge=1, strict=True)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("name", "reason")
    @classmethod
    def meaningful(cls, value):
        if not value.strip():
            raise ValueError("Field is required")
        return value.strip()


class OpsSupplierSettingsInput(DTO):
    lead_time_days: int = Field(ge=1, le=365, strict=True)
    expected_version: int = Field(ge=0, strict=True)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def reason_required(cls, value):
        if not value.strip():
            raise ValueError("Reason is required")
        return value.strip()


class OpsOrderLineInput(DTO):
    item_id: int = Field(gt=0, strict=True)
    warehouse_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, le=MAX_QTY, strict=True)


class OpsOrderInput(DTO):
    supplier_id: int = Field(gt=0, strict=True)
    ordered_on: date
    note: str = Field(default="", max_length=1000)
    lines: list[OpsOrderLineInput] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_products(self):
        if len({(line.item_id, line.warehouse_id) for line in self.lines}) != len(self.lines):
            raise ValueError("Duplicate product/location")
        return self


class OpsOrderUpdate(OpsOrderInput):
    expected_version: int = Field(ge=1, strict=True)


class OpsOrderTransition(DTO):
    expected_version: int = Field(ge=1, strict=True)
    reason: str = Field(default="", max_length=1000)


class OpsReceiptLineInput(DTO):
    order_line_id: int = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, le=MAX_QTY, strict=True)


class OpsReceiptInput(DTO):
    expected_version: int = Field(ge=1, strict=True)
    occurred_on: date
    external_ref: str = Field(min_length=1, max_length=120)
    reason: str = Field(default="", max_length=1000)
    lines: list[OpsReceiptLineInput] = Field(min_length=1, max_length=200)

    @field_validator("external_ref")
    @classmethod
    def valid_reference(cls, value):
        if not value.strip():
            raise ValueError("Delivery reference is required")
        return value.strip()

    @model_validator(mode="after")
    def unique_lines(self):
        if len({line.order_line_id for line in self.lines}) != len(self.lines):
            raise ValueError("Duplicate order line")
        return self


class OpsMovementInput(DTO):
    item_id: int = Field(gt=0, strict=True)
    warehouse_id: int = Field(gt=0, strict=True)
    quantity: int = Field(ge=0, le=MAX_QTY, strict=True)
    expected_balance_version: int = Field(ge=0, strict=True)
    occurred_on: date
    external_ref: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason", "external_ref")
    @classmethod
    def text_required(cls, value):
        if not value.strip():
            raise ValueError("A reference and reason are required")
        return value.strip()
