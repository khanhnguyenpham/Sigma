from typing import Literal
from fastapi import APIRouter, Header, Query, Request, Response
from core.errors import DomainError
from modules.dealers import service
from modules.dealers.schemas import DealerInput, DealerUpdate, DealerRequestInput, Transition, Rejection, IssueInput
from modules.operations.router import actor

router = APIRouter(prefix="/api/v1/dealers", tags=["dealers"])
portal = APIRouter(prefix="/api/v1/dealer", tags=["dealer portal"])
Status = Literal["submitted", "approved", "rejected", "cancelled", "issued", "received"]


def dealer_scope(request):
    """The dealer comes from the session only; a caller-supplied dealer id is never trusted."""
    user = getattr(request.state, "user", None)
    if not user or user["role"] != "dealer" or user.get("dealer_id") is None:
        raise DomainError("dealer_required", "Trang này dành cho tài khoản đại lý.", 403)
    return user["dealer_id"], user["id"]


@router.get("")
def list_dealers(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), active: bool | None = None,
        search: str | None = Query(None, max_length=120)):
    actor(request)
    with request.app.state.sessions() as session:
        return service.dealers(session, page, page_size, active, search)


@router.post("", status_code=201)
def create_dealer(payload: DealerInput, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.create_dealer(session, payload, user)


@router.patch("/{key}")
def update_dealer(key: int, payload: DealerUpdate, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.update_dealer(session, key, payload, user)


@router.get("/requests")
def list_requests(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
        status: Status | None = None, dealer_id: int | None = Query(None, gt=0)):
    actor(request)
    with request.app.state.sessions() as session:
        return service.requests(session, page, page_size, dealer_id, status)


@router.get("/requests/{key}")
def get_request(key: int, request: Request):
    actor(request)
    with request.app.state.sessions() as session:
        return service.request_view(session, key)


@router.post("/requests/{key}/approve")
def approve(key: int, payload: Transition, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.approve(session, key, payload, user)


@router.post("/requests/{key}/reject")
def reject(key: int, payload: Rejection, request: Request):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.reject(session, key, payload, user)


@router.post("/requests/{key}/issue")
def issue(key: int, payload: IssueInput, request: Request, idempotency_key: str = Header(alias="Idempotency-Key")):
    user = actor(request)
    with request.app.state.sessions.begin() as session:
        return service.issue(session, key, payload, idempotency_key, user)[0]


@portal.get("/products")
def portal_products(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), search: str | None = Query(None, max_length=120),
        in_stock: bool = False, product_type: Literal["eSIM", "physical_SIM"] | None = None, country: str | None = Query(None, max_length=100),
        carrier: str | None = Query(None, max_length=100)):
    dealer_scope(request)
    with request.app.state.sessions() as session:
        return service.available_products(session, page, page_size, search, in_stock, product_type, country, carrier)


@portal.get("/product-filters")
def portal_product_filters(request: Request):
    dealer_scope(request)
    with request.app.state.sessions() as session:
        return service.product_filters(session)


@portal.get("/requests")
def portal_requests(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), status: Status | None = None):
    dealer, _ = dealer_scope(request)
    with request.app.state.sessions() as session:
        return service.requests(session, page, page_size, dealer, status)


@portal.get("/requests/{key}")
def portal_request(key: int, request: Request):
    dealer, _ = dealer_scope(request)
    with request.app.state.sessions() as session:
        return service.request_view(session, key, dealer)


@portal.post("/requests", status_code=201)
def portal_create(payload: DealerRequestInput, request: Request, response: Response, idempotency_key: str = Header(alias="Idempotency-Key")):
    dealer, user = dealer_scope(request)
    with request.app.state.sessions.begin() as session:
        result, created = service.create_request(session, dealer, payload, idempotency_key, user)
        response.status_code = 201 if created else 200
        return result


@portal.post("/requests/{key}/cancel")
def portal_cancel(key: int, payload: Transition, request: Request):
    dealer, user = dealer_scope(request)
    with request.app.state.sessions.begin() as session:
        return service.cancel(session, key, payload, dealer, user)


@portal.post("/requests/{key}/receive")
def portal_receive(key: int, payload: Transition, request: Request):
    dealer, user = dealer_scope(request)
    with request.app.state.sessions.begin() as session:
        return service.receive(session, key, payload, dealer, user)


@portal.get("/stock")
def portal_stock(request: Request, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)):
    dealer, _ = dealer_scope(request)
    with request.app.state.sessions() as session:
        return service.dealer_stock(session, dealer, page, page_size)
