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
    trade_lifecycle_profile: str | None = None
    internal_status: str | None = None
    internal_reason: str | None = None
    internal_stop_change_id: int | None = None
    internal_version: int | None = None
    provider_status: str | None = None
    provider_blockers: list[dict[str,Any]] | None = None
    provider_restrictions: list[dict[str,Any]] | None = None
    sales_allowed: bool | None = None
    provider_notice_ids: list[int] | None = None
    provider_reasons: list[str] | None = None
    provider_sources: list[dict[str,Any]] | None = None
    replenishment_block_reasons: list[str] | None = None
    decision_origin: date | None = None
    rights_on: date | None = None
    q_policy: int | None = None
    q_final: int | None = None
    cap_reason: str | None = None
    sellable_budget: int | None = None
    provider_stop_on: date | None = None
    cap_eta: date | None = None
    forecast_coverage_complete: bool | None = None
    quantity_diagnostics_available: bool | None = None
    total_qty: int | None = None
    sellable_qty: int | None = None
    blocked_qty: int | None = None
    needs_supplier_action: bool | None = None
    actionable: bool | None = None
    metric_basis: str | None = None


class AlertPage(DTO):
    context: dict[str, Any]
    items: list[AlertRow]
    total: int
    page: int
    page_size: int
