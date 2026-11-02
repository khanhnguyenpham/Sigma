from pydantic import Field, model_validator
from core.schemas import DTO
from datetime import date
from typing import Literal

SupplyStatus = Literal["active", "scheduled_stop", "stopped"]


class SupplyChangeCreate(DTO):
    action: Literal["stop", "cancel_stop", "resume"]
    known_on: date
    effective_on: date
    target_change_id: int | None = Field(default=None, gt=0, strict=True)
    reason: str = Field(min_length=1, max_length=1000)
    expected_version: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def valid_notice(self):
        from modules.catalog.supply import validate_supply_change
        # Structural validation only; timeline validation is serialized in the service.
        self.reason = self.reason.strip()
        if not self.reason:
            raise ValueError("Reason cannot be blank")
        if self.action == "stop":
            validate_supply_change([], item_id=0, action=self.action, known_on=self.known_on,
                                   effective_on=self.effective_on, target_change_id=self.target_change_id)
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
