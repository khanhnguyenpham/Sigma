"""Alert result tables and whole-run replay diagnostics."""
import uuid
from typing import Annotated
from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from modules.alerts.models import Alert
from modules.alerts.service import opportunity_breakdown
from modules.alerts.schemas import WholeRun
from core.errors import DomainError
from core.run_context import required_run
from modules.reporting.schemas import Filters
from modules.reporting.service import context
from modules.reporting.router import result_response

router = APIRouter(prefix="/api/v1/runs")

@router.get("/{key}/alerts")
def alerts(key: uuid.UUID, request: Request, filters: Annotated[Filters, Query()]):
    return result_response(request, key, "alerts", filters)


@router.get("/{key}/alert-opportunities")
def alert_opportunities(
    key: uuid.UUID, request: Request, filters: Annotated[WholeRun, Query()]
):
    with request.app.state.sessions() as session:
        run = required_run(session, key, "alert_replay", complete=True)
        cases = (
            session.execute(
                select(
                    Alert.as_of_date,
                    Alert.actual_depletion_date,
                    Alert.predicted_depletion_date,
                    Alert.is_evaluable,
                ).where(Alert.run_id == key, Alert.alert_type == "depletion")
            )
            .mappings()
            .all()
        )
        try:
            diagnostic = opportunity_breakdown(cases)
        except ValueError:
            raise DomainError(
                "verification_failed", "Invalid replay event window", 409
            ) from None
        official = run.result_summary.get("alert_metrics", {})
        if any(
            official.get(k) != diagnostic[v]
            for k, v in [
                ("early_numerator", "observed_early_numerator"),
                ("event_denominator", "event_denominator"),
                ("excluded_count", "excluded_count"),
            ]
        ):
            raise DomainError(
                "verification_failed",
                "Replay diagnostic differs from verified summary",
                409,
            )
        return dict(context=context(run), diagnostic=diagnostic)
