"""Local API foundation. No request performs model fitting or raw-file upload."""

from contextlib import asynccontextmanager
import uuid
from fastapi import FastAPI, Header, Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sigma_m3.db import database
from sigma_m3.errors import DomainError
from sigma_m3.models import Warehouse, Item, Supplier, Policy, Run, Scenario
from sigma_m3.schemas import PolicyCreate, RunCreate, WarehouseUpdate, ScenarioCreate
from sigma_m3.services.catalog import create_policy
from sigma_m3.services.runs import enqueue, required_run
from sigma_m3.settings import Settings


def record(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def run_view(row):
    # Detailed config, manifest file paths and request payload are private.
    return {
        name: getattr(row, name)
        for name in [
            "id",
            "kind",
            "status",
            "source_import_run_id",
            "forecast_run_id",
            "scenario_id",
            "as_of_date",
            "observation_end",
            "config_version",
            "assumption_version",
            "target_version",
            "created_at",
            "started_at",
            "finished_at",
            "heartbeat_at",
            "error_code",
            "result_summary",
            "period_start",
            "period_end",
        ]
    }


def create_app(settings=None):
    settings = settings or Settings.from_env()
    engine, sessions = database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="SIGMA M3 local API", version="0.1.0", lifespan=lifespan)
    app.state.engine, app.state.sessions, app.state.settings = (
        engine,
        sessions,
        settings,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse(
            status_code=exc.status,
            content={
                "error": dict(code=exc.code, message=exc.message, details=exc.details),
                "request_id": str(uuid.uuid4()),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Pydantic's default error can echo submitted values. Return field/type only.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_input",
                    "message": "Invalid request fields",
                    "details": {
                        "fields": [
                            {"location": list(e["loc"]), "type": e["type"]}
                            for e in exc.errors()
                        ]
                    },
                },
                "request_id": str(uuid.uuid4()),
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity(request, exc):
        return await domain_error(
            request,
            DomainError(
                "version_conflict", "Database constraint rejected the change", 409
            ),
        )

    @app.exception_handler(OperationalError)
    async def unavailable(request, exc):
        return await domain_error(
            request, DomainError("database_unavailable", "Database is unavailable", 503)
        )

    @app.get("/api/v1/health")
    def health():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable", "profile": "m3-design-v1"}

    def listing(model, page, size, predicates=()):
        with sessions() as session:
            query = select(model).where(*predicates)
            total = session.scalar(select(func.count()).select_from(query.subquery()))
            rows = session.scalars(
                query.order_by(model.id).offset((page - 1) * size).limit(size)
            ).all()
            return {
                "items": [record(r) for r in rows],
                "total": total,
                "page": page,
                "page_size": size,
            }

    @app.get("/api/v1/warehouses")
    def warehouses(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        country: str | None = None,
        run_id: uuid.UUID | None = None,
    ):
        if run_id:
            from sigma_m3.api.results import snapshot_maps

            with sessions() as s:
                run = required_run(s, run_id, complete=True)
                rows = list(snapshot_maps(s, run)[0].values())
                if country:
                    rows = [r for r in rows if r["destination_country"] == country]
                return dict(
                    items=rows[(page - 1) * page_size : page * page_size],
                    total=len(rows),
                    page=page,
                    page_size=page_size,
                )
        return listing(
            Warehouse,
            page,
            page_size,
            [Warehouse.destination_country == country] if country else [],
        )

    @app.patch("/api/v1/warehouses/{key}")
    def warehouse_patch(key: int, request: WarehouseUpdate):
        with sessions.begin() as s:
            row = s.scalar(
                select(Warehouse).where(Warehouse.id == key).with_for_update()
            )
            if row is None:
                raise DomainError("not_found", "Warehouse does not exist", 404)
            if row.version != request.expected_version:
                raise DomainError("version_conflict", "Warehouse changed; reload", 409)
            row.city = request.city
            row.version += 1
            s.flush()
            return jsonable_encoder(record(row))

    @app.get("/api/v1/items")
    def items(
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
        warehouse_id: int | None = Query(None, gt=0),
        product_type: str | None = None,
        run_id: uuid.UUID | None = None,
        search: str | None = None,
    ):
        if run_id:
            from sigma_m3.api.results import snapshot_maps

            with sessions() as s:
                run = required_run(s, run_id, complete=True)
                rows = [{**v, "id": k} for k, v in snapshot_maps(s, run)[1].items()]
                if warehouse_id:
                    rows = [r for r in rows if r["warehouse_id"] == warehouse_id]
                if product_type:
                    rows = [r for r in rows if r["product_type"] == product_type]
                if search:
                    rows = [r for r in rows if search.casefold() in r["sku"].casefold()]
                return dict(
                    items=rows[(page - 1) * page_size : page * page_size],
                    total=len(rows),
                    page=page,
                    page_size=page_size,
                )
        filters = []
        if warehouse_id:
            filters.append(Item.warehouse_id == warehouse_id)
        if product_type:
            filters.append(Item.product_type == product_type)
        if search:
            filters.append(Item.sku.icontains(search, autoescape=True))
        return listing(Item, page, page_size, filters)

    @app.get("/api/v1/suppliers")
    def suppliers(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
        return listing(Supplier, page, page_size)

    @app.get("/api/v1/supplier-item-policies")
    def policies(
        item_id: int | None = None,
        supplier_id: int | None = None,
        effective_on: __import__("datetime").date | None = None,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=100),
    ):
        filters = []
        if item_id:
            filters.append(Policy.item_id == item_id)
        if supplier_id:
            filters.append(Policy.supplier_id == supplier_id)
        if effective_on:
            filters.extend(
                [
                    Policy.effective_from <= effective_on,
                    (Policy.effective_to.is_(None))
                    | (Policy.effective_to > effective_on),
                ]
            )
        with sessions() as s:
            query = (
                select(Policy, Item, Warehouse, Supplier)
                .join(Item, Item.id == Policy.item_id)
                .join(Warehouse, Warehouse.id == Item.warehouse_id)
                .join(Supplier, Supplier.id == Policy.supplier_id)
                .where(*filters)
            )
            total = s.scalar(select(func.count()).select_from(query.subquery()))
            rows = s.execute(
                query.order_by(Policy.item_id, Policy.version.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return dict(
                items=[
                    {
                        **record(p),
                        "item_label": f"{w.destination_country} / {w.carrier} · {i.sku} · {i.product_type}",
                        "supplier_code": supplier.code,
                    }
                    for p, i, w, supplier in rows
                ],
                total=total,
                page=page,
                page_size=page_size,
            )

    @app.post("/api/v1/supplier-item-policies", status_code=201)
    def policy(request: PolicyCreate):
        with sessions.begin() as session:
            row = create_policy(session, request)
            return jsonable_encoder(record(row))

    @app.get("/api/v1/scenarios")
    def scenarios(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
        return listing(Scenario, page, page_size)

    @app.post("/api/v1/scenarios", status_code=201)
    def scenario(request: ScenarioCreate):
        with sessions.begin() as s:
            s.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:code))"),
                {"code": request.code},
            )
            if (
                request.base_scenario_id
                and s.get(Scenario, request.base_scenario_id) is None
            ):
                raise DomainError("not_found", "Base scenario does not exist", 404)
            ids = {o.item_id for o in request.settings.policy_overrides} | {
                r.item_id for r in request.settings.receipts_initial
            }
            if ids - set(s.scalars(select(Item.id).where(Item.id.in_(ids)))):
                raise DomainError("not_found", "Scenario contains an unknown item", 404)
            version = (
                s.scalar(
                    select(func.max(Scenario.version)).where(
                        Scenario.code == request.code
                    )
                )
                or 0
            ) + 1
            row = Scenario(
                code=request.code,
                version=version,
                name=request.name,
                description=request.description,
                settings=request.settings.model_dump(mode="json", exclude_none=True),
                assumption_version="user_scenario_v1",
            )
            s.add(row)
            s.flush()
            return jsonable_encoder(record(row))

    @app.post("/api/v1/runs")
    def runs_post(
        request: RunCreate, idempotency_key: str = Header(alias="Idempotency-Key")
    ):
        with sessions.begin() as session:
            row, created = enqueue(session, request, idempotency_key)
            return JSONResponse(
                status_code=202 if created else 200,
                content=jsonable_encoder(
                    dict(
                        run_id=row.id,
                        status=row.status,
                        status_url=f"/api/v1/runs/{row.id}",
                    )
                ),
            )

    @app.get("/api/v1/runs")
    def runs_get(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)):
        with sessions() as session:
            rows = session.scalars(
                select(Run)
                .order_by(Run.created_at.desc(), Run.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            output = []
            for row in rows:
                r = run_view(row)
                r["result_summary"] = {
                    k: v
                    for k, v in r["result_summary"].items()
                    if k not in {"metrics", "selections", "audit"}
                }
                output.append(r)
            return dict(
                items=output,
                total=session.scalar(select(func.count()).select_from(Run)),
                page=page,
                page_size=page_size,
            )

    @app.get("/api/v1/runs/{key}")
    def run_get(key: uuid.UUID):
        with sessions() as session:
            return run_view(required_run(session, key))

    @app.get("/api/v1/runs/{key}/summary")
    def run_summary(key: uuid.UUID):
        with sessions() as session:
            row = required_run(session, key, complete=True)
            return dict(context=run_view(row), summary=row.result_summary)

    from sigma_m3.api.results import router

    from sigma_m3.api.monthly import router as monthly_router

    app.include_router(monthly_router)
    app.include_router(router)
    frontend = (
        __import__("pathlib").Path(__file__).resolve().parents[3] / "frontend/dist"
    )
    if frontend.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app
