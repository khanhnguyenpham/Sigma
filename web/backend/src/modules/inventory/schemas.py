from datetime import date
from typing import Literal
from pydantic import Field
from core.schemas import DTO

class WorkspaceFilters(DTO):
    as_of_date: date
    warehouse_id: int | None = Field(default=None, gt=0)
    item_id: int | None = Field(default=None, gt=0)
    supplier_id: int | None = Field(default=None, gt=0)
    product_type: Literal["eSIM", "physical_SIM"] | None = None
