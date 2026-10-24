"""HTTP error handling, row serialization and shared catalog pagination."""
import uuid
from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, OperationalError
from core.errors import DomainError

router = APIRouter(prefix="/api/v1")


def record(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def listing(sessions, model, page, size, predicates=()):
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


def install_error_handlers(app):
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


@router.get("/health")
def health(http: Request):
    with http.app.state.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable", "profile": "m3-design-v1"}
