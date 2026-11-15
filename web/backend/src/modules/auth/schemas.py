from typing import Literal
from pydantic import Field, SecretStr, field_validator, model_validator
from core.schemas import DTO


class LoginInput(DTO):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9][a-z0-9._-]{2,63}$")
    password: SecretStr

    @field_validator("password")
    @classmethod
    def bounded_password(cls, value):
        if not 1 <= len(value.get_secret_value()) <= 128:
            raise ValueError("Invalid password length")
        return value


class UserCreate(LoginInput):
    display_name: str = Field(min_length=1, max_length=100)
    role: Literal["admin", "supplier"]
    supplier_id: int | None = Field(default=None, ge=1)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Name is required")
        return value.strip()

    @model_validator(mode="after")
    def valid_scope(self):
        if (self.role == "supplier") != (self.supplier_id is not None):
            raise ValueError("Supplier role requires exactly one supplier")
        if len(self.password.get_secret_value()) < 12:
            raise ValueError("Use at least 12 characters")
        return self


class UserActive(DTO):
    active: bool
