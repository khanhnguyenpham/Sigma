from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import Field, model_validator
from core.schemas import DTO


class PolicyCreate(DTO):
    item_id: int = Field(gt=0, strict=True)
    supplier_id: int = Field(gt=0, strict=True)
    effective_from: date
    configured_rop_floor: int = Field(ge=0, le=2**63 - 1, strict=True)
    moq: int = Field(ge=1, le=2**63 - 1, strict=True)
    safety_days: Decimal = Field(ge=0, max_digits=8, decimal_places=3)
    expected_version: int = Field(ge=0, strict=True)


class ReceiptInput(DTO):
    item_id: int = Field(gt=0, strict=True)
    ordered_on: date
    eta: date
    ordered_qty: int = Field(gt=0, le=2**63 - 1, strict=True)
    lot_key: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def eta7(self):
        if (self.eta - self.ordered_on).days != 7:
            raise ValueError("ETA must be ordered_on plus seven calendar days")
        return self


class PolicyOverride(DTO):
    item_id: int = Field(gt=0, strict=True)
    supplier_id: int | None = Field(default=None, gt=0, strict=True)
    configured_rop_floor: int | None = Field(
        default=None, ge=0, le=2**63 - 1, strict=True
    )
    moq: int | None = Field(default=None, ge=1, le=2**63 - 1, strict=True)
    safety_days: Decimal | None = Field(
        default=None, ge=0, max_digits=8, decimal_places=3
    )


class ScenarioSettings(DTO):
    cover_days: Literal[3, 7, 14]
    safety_multiplier: float = Field(ge=0, le=10)
    policy_overrides: list[PolicyOverride]
    receipts_initial: list[ReceiptInput]
    receipts_declared: Literal[True]

    @model_validator(mode="after")
    def unique_keys(self):
        ids = [o.item_id for o in self.policy_overrides]
        lots = [o.lot_key for o in self.receipts_initial]
        if len(ids) != len(set(ids)) or len(lots) != len(set(lots)):
            raise ValueError("Duplicate override or receipt keys")
        return self


class ScenarioCreate(DTO):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    base_scenario_id: int | None = Field(default=None, gt=0, strict=True)
    settings: ScenarioSettings
    description: str = Field(default="", max_length=1000)
