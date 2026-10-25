from typing import Literal
from pydantic import Field
from modules.inventory.schemas import WorkspaceFilters

class PurchasingFilters(WorkspaceFilters):
    view: Literal["recommendations", "incoming", "history"] = "recommendations"
    search: str = Field(default="", max_length=80)
    sort: Literal["quantity_desc", "quantity_asc", "eta_asc", "ordered_desc"] = (
        "quantity_desc"
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
