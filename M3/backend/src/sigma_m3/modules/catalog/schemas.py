from pydantic import Field, model_validator
from sigma_m3.core.schemas import DTO


class WarehouseUpdate(DTO):
    city: str = Field(min_length=1, max_length=100)
    expected_version: int = Field(ge=1, strict=True)

    @model_validator(mode="after")
    def city_not_blank(self):
        self.city = self.city.strip()
        if not self.city:
            raise ValueError("City cannot be blank")
        return self
