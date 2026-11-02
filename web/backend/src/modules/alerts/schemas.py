from core.schemas import DTO
from datetime import date
from typing import Any, Literal


class WholeRun(DTO):
    """Diagnostic denominators must not silently change with table filters."""


class AlertRow(DTO):
    id: int
    window_origin: date
    item_id: int
    as_of_date: date
    alert_type: Literal["below_rop", "depletion", "projected_below_rop"]
    state: Literal["low_stock", "pending_covers", "urgent", "early", "already_depleted", "not_within_horizon", "threshold_warning"]
    predicted_threshold_date: date | None
    predicted_depletion_date: date | None
    actual_depletion_date: date | None
    lead_days: int | None
    is_evaluable: bool
    evaluation_class: Literal["TP", "FP", "FN", "TN"] | None
    exclusion_reason: str | None
    explanation: dict[str, Any]
    is_simulated: bool
    warehouse_id: int
    sku: str
    product_type: Literal["eSIM", "physical_SIM"]
    destination_country: str
    carrier: str
    city: str | None
    display_city: str | None = None
    supply_status: Literal["active", "scheduled_stop", "stopped"] | None = None
    replenishment_allowed: bool = True
    replenishment_block_reason: str | None = None
    stock_below_rop: bool | None = None
    sell_through_state: Literal["selling_remaining", "waiting_receipts", "sold_out"] | None = None


class AlertPage(DTO):
    context: dict[str, Any]
    items: list[AlertRow]
    total: int
    page: int
    page_size: int
