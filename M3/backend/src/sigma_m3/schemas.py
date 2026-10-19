from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class PolicyCreate(DTO):
    item_id: int = Field(gt=0, strict=True)
    supplier_id: int = Field(gt=0, strict=True)
    effective_from: date
    configured_rop_floor: int = Field(ge=0, le=2**63 - 1, strict=True)
    moq: int = Field(ge=1, le=2**63 - 1, strict=True)
    safety_days: Decimal = Field(ge=0, max_digits=8, decimal_places=3)
    expected_version: int = Field(ge=0, strict=True)


class RunCreate(DTO):
    kind: Literal[
        "source_import", "forecast", "policy_replay", "alert_replay", "stock_projection"
    ]
    as_of_date: date
    source_key: Literal["orders_snapshot"] | None = None
    source_import_run_id: UUID | None = None
    forecast_run_id: UUID | None = None
    retry_of_run_id: UUID | None = None
    scenario_id: int | None = Field(default=None, gt=0, strict=True)
    period_start: date | None = None
    period_end: date | None = None
    mode: Literal["replay", "future"] | None = None

    @model_validator(mode="after")
    def correct_kind(self):
        if self.kind == "source_import":
            if (
                not self.source_key
                or self.source_import_run_id
                or self.forecast_run_id
                or self.scenario_id
                or self.mode
            ):
                raise ValueError("Source import requires only a registered source key")
        elif not self.source_import_run_id or self.source_key:
            raise ValueError("A source import parent is required")
        if self.kind == "forecast":
            if (
                not self.mode
                or self.scenario_id
                or (self.mode == "future" and not self.forecast_run_id)
            ):
                raise ValueError(
                    "Forecast mode and compatible selection parent are required"
                )
        elif self.mode:
            raise ValueError("Mode applies only to forecasts")
        if self.kind in {"policy_replay", "alert_replay", "stock_projection"} and (
            not self.forecast_run_id or not self.scenario_id
        ):
            raise ValueError("Inventory needs a forecast parent and declared scenario")
        if self.kind.endswith("replay"):
            if (
                not self.period_start
                or not self.period_end
                or self.period_end < self.period_start
                or (self.period_start - self.as_of_date).days != 1
            ):
                raise ValueError(
                    "Replay period must start immediately after as_of_date"
                )
        elif self.period_start or self.period_end:
            raise ValueError("This run kind does not accept a replay period")
        return self


class WarehouseUpdate(DTO):
    city: str = Field(min_length=1, max_length=100)
    expected_version: int = Field(ge=1, strict=True)

    @model_validator(mode="after")
    def city_not_blank(self):
        self.city = self.city.strip()
        if not self.city:
            raise ValueError("City cannot be blank")
        return self


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
