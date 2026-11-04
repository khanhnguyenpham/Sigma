from pydantic import Field, model_validator
from core.schemas import DTO
from datetime import date
from typing import Literal
from uuid import UUID

SupplyStatus = Literal["active", "scheduled_stop", "stopped"]


class ReceivingWarehouseUpdate(DTO):
    receiving_warehouse_id: int = Field(gt=0, strict=True)
    expected_version: int = Field(ge=0, strict=True)


class SupplyChangeCreate(DTO):
    action: Literal["stop", "cancel_stop", "resume"]
    known_on: date
    effective_on: date
    target_change_id: int | None = Field(default=None, gt=0, strict=True)
    reason: str = Field(min_length=1, max_length=1000)
    expected_version: int = Field(ge=0, strict=True)
    preview_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    impact_run_id: UUID | None = None
    impact_as_of_date: date | None = None

    @model_validator(mode="after")
    def valid_notice(self):
        from modules.catalog.supply import validate_supply_change
        # Structural validation only; timeline validation is serialized in the service.
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError("Reason cannot be blank")
        if self.impact_as_of_date is not None and self.impact_run_id is None:
            raise ValueError("Impact date needs an impact run")
        if self.action == "stop":
            validate_supply_change([], item_id=0, action=self.action, known_on=self.known_on,
                                   effective_on=self.effective_on, target_change_id=self.target_change_id,
                                   minimum_notice_days=0)
        elif self.target_change_id is None or self.effective_on != self.known_on:
            raise ValueError("Cancel/resume needs a target and takes effect on known_on")
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
