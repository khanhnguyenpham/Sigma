"""Provider notice management, separate from internal replenishment decisions."""
from datetime import date
from typing import Annotated
from fastapi import APIRouter, Query, Request
from fastapi.encoders import jsonable_encoder
from modules.catalog.provider_schemas import (ProviderPreview, ProviderStopCreate, ProviderFollowCreate,
                                              ProviderFollowDraft, ProviderNoticeFilters)
from modules.catalog.provider_read import list_notices, get_notice, get_notice_items
from modules.catalog.trade_preview import provider_preview

router = APIRouter(prefix="/api/v1/provider-product-notices")


@router.get("")
def notice_list(http: Request, filters: Annotated[ProviderNoticeFilters, Query()]):
    with http.app.state.sessions() as session:
        return jsonable_encoder(list_notices(session, **filters.model_dump()))


@router.post("/preview")
def preview(http: Request, draft: ProviderPreview, page: int = Query(1, ge=1),
            page_size: int = Query(50, ge=1, le=100)):
    with http.app.state.sessions.begin() as session:
        result = provider_preview(session, draft)
        result["items"] = result["items"][(page-1)*page_size:page*page_size]
        return jsonable_encoder(dict(result, page=page, page_size=page_size))


@router.post("", status_code=201)
def create(http: Request, draft: ProviderStopCreate):
    with http.app.state.sessions.begin() as session:
        return jsonable_encoder(provider_preview(session, draft, write=True, fingerprint=draft.preview_fingerprint))


@router.get("/{key}")
def detail(http: Request, key: int, as_of_date: date | None = None):
    with http.app.state.sessions() as session:
        header, _ = get_notice(session, key, as_of_date)
        return jsonable_encoder(header)


@router.get("/{key}/events")
def events(http: Request, key: int, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
    with http.app.state.sessions() as session:
        header, root = get_notice(session, key)
        rows = list(reversed(root["events"]))
        return jsonable_encoder(dict(items=rows[(page-1)*page_size:page*page_size], total=len(rows),
            page=page, page_size=page_size, latest_version=header["latest_version"]))


@router.get("/{key}/items")
def affected_items(http: Request, key: int, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
                   as_of_date: date | None = None):
    with http.app.state.sessions() as session:
        return jsonable_encoder(get_notice_items(session, key, as_of_date, page, page_size))


def followup(http, key, action, request):
    draft = ProviderFollowDraft(notice_id=key, action=action, **request.model_dump(exclude={"preview_fingerprint"}))
    with http.app.state.sessions.begin() as session:
        return jsonable_encoder(provider_preview(session, draft, write=True, fingerprint=request.preview_fingerprint))


@router.post("/{key}/cancel", status_code=201)
def cancel(http: Request, key: int, request: ProviderFollowCreate):
    return followup(http, key, "cancel_stop", request)


@router.post("/{key}/resume", status_code=201)
def resume(http: Request, key: int, request: ProviderFollowCreate):
    return followup(http, key, "resume_supply", request)
