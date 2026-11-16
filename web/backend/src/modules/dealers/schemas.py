from datetime import date
from pydantic import Field, field_validator, model_validator
from core.schemas import DTO
from modules.operations.schemas import MAX_QTY


def _required(value):
    if not value.strip():
        raise ValueError("Field is required")
    return value.strip()


class DealerInput(DTO):
    code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(default="", max_length=200)

    @field_validator("code", "name")
    @classmethod
    def meaningful(cls, value):
        return _required(value)


class DealerUpdate(DTO):
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(default="", max_length=200)
    active: bool
    expected_version: int = Field(ge=1, strict=True)

    @field_validator("name")
    @classmethod
    def meaningful(cls, value):
        return _required(value)


class RequestLineInput(DTO):
    item_id: int = Field(ge=1)
    quantity: int = Field(ge=1, le=MAX_QTY, strict=True)


class DealerRequestInput(DTO):
    note: str = Field(default="", max_length=1000)
    lines: list[RequestLineInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_items(self):
        if len({line.item_id for line in self.lines}) != len(self.lines):
            raise ValueError("Each product may appear once")
        return self


class Transition(DTO):
    expected_version: int = Field(ge=1, strict=True)


class Rejection(Transition):
    reason: str = Field(min_length=1, max_length=1000)

    @field_validator("reason")
    @classmethod
    def meaningful(cls, value):
        return _required(value)


class IssueInput(Transition):
    warehouse_id: int = Field(ge=1)
    occurred_on: date
