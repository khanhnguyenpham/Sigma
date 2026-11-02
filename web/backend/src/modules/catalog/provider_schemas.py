"""Separate request shapes for internal stops and provider notice operations."""
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator
from core.schemas import DTO
from modules.catalog.provider import provider_event_values

ProviderStatus = Literal["clear", "scheduled_stop", "stopped", "scheduled_resume"]
PositiveId = Annotated[int, Field(gt=0, strict=True)]
Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ScopeProduct(DTO):
    sku: str = Field(min_length=1, max_length=200)
    product_type: Literal["eSIM", "physical_SIM"]
    destination_countries: list[str] = Field(min_length=1)
    warehouse_ids: list[PositiveId] = Field(min_length=1)


class ProviderScope(DTO):
    products: list[ScopeProduct] = Field(min_length=1)


class ImpactContext(DTO):
    impact_run_id: UUID | None = None
    impact_as_of_date: date | None = None

    @model_validator(mode="after")
    def paired_impact_context(self):
        if self.impact_as_of_date is not None and self.impact_run_id is None:
            raise ValueError("Impact date needs an impact run")
        return self


class ProviderEventDraft(ImpactContext):
    known_on: date
    effective_on: date
    reason: str = Field(min_length=1, max_length=1000)
    source_description: str = Field(min_length=1, max_length=1000)
    source_ref: str | None = Field(default=None, max_length=2048)
    expected_version: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def declared_source(self):
        values = provider_event_values(action="stop", known_on=self.known_on, effective_on=self.effective_on,
            reason=self.reason, source_description=self.source_description, source_ref=self.source_ref)
        self.reason, self.source_description = values["reason"], values["source_description"]
        return self


class ProviderStopDraft(ProviderEventDraft):
    action: Literal["stop"] = "stop"
    supplier_id: PositiveId
    scope_definition: ProviderScope


class ProviderFollowDraft(ProviderEventDraft):
    action: Literal["cancel_stop", "resume_supply"]
    notice_id: PositiveId
    target_event_id: PositiveId


class ProviderStopCreate(ProviderStopDraft):
    preview_fingerprint: Fingerprint


class ProviderFollowCreate(ProviderEventDraft):
    target_event_id: PositiveId
    preview_fingerprint: Fingerprint


ProviderPreview = Annotated[ProviderStopDraft | ProviderFollowDraft, Field(discriminator="action")]


class ProviderNoticeFilters(DTO):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    supplier_id: int | None = Field(default=None, gt=0)
    item_id: int | None = Field(default=None, gt=0)
    warehouse_id: int | None = Field(default=None, gt=0)
    sku: str | None = Field(default=None, max_length=200)
    product_type: Literal["eSIM", "physical_SIM"] | None = None
    destination_country: str | None = None
    status: ProviderStatus | None = None
    as_of_date: date | None = None
    search: str | None = Field(default=None, max_length=200)
