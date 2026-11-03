from datetime import date
from typing import Literal
from pydantic import Field
from core.schemas import DTO

class TradeFilters(DTO):
    sku: str | None = Field(default=None, min_length=1, max_length=200)
    destination_country: str | None = Field(default=None, min_length=1, max_length=100)
    carrier: str | None = Field(default=None, min_length=1, max_length=100)
    window_origin: date | None = None
    internal_status: Literal['active', 'scheduled_stop', 'stopped'] | None = None
    provider_status: Literal['clear', 'scheduled_stop', 'stopped', 'scheduled_resume'] | None = None
    replenishment_allowed: bool | None = None
    sales_allowed: bool | None = None


class Filters(TradeFilters):
    split: Literal["validation", "test", "future"] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    warehouse_id: int | None = Field(default=None, gt=0)
    item_id: int | None = Field(default=None, gt=0)
    supplier_id: int | None = Field(default=None, gt=0)
    product_type: Literal["eSIM", "physical_SIM"] | None = None
    date_from: date | None = None
    date_to: date | None = None
    as_of_date: date | None = None
    block: int | None = Field(default=None, ge=1, le=2)
    state: str | None = None
    alert_type: Literal["below_rop", "depletion", "projected_below_rop"] | None = None
    granularity: Literal["weekly", "allocated_daily", "alert", "policy", "threshold"] | None = None
    cadence: Literal["daily_origins", "nonoverlapping_7d"] | None = None
    aggregate: Literal["route_day"] | None = None
