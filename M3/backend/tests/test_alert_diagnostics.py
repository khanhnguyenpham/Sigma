from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sigma_m3.services.alerts import opportunity_breakdown
from sigma_m3.main import create_app
from sigma_m3.models import Alert, Run
from test_results_api import result_fixture
from test_postgres_api import settings

D = date(2025, 10, 31)


def case(actual, predicted, evaluable=True):
    return dict(
        as_of_date=D,
        is_evaluable=evaluable,
        actual_depletion_date=D + timedelta(days=actual)
        if actual is not None
        else None,
        predicted_depletion_date=D + timedelta(days=predicted)
        if predicted is not None
        else None,
    )


def test_opportunity_ceiling_keeps_early_failures_in_official_denominator():
    result = opportunity_breakdown(
        [
            case(6, 8),
            case(7, 5),
            case(14, None),
            case(None, 9),
            case(None, None),
            case(0, 0, False),
        ]
    )
    assert result["event_denominator"] == 3
    assert result["short_notice_events"] == 1
    assert result["eligible_early_events"] == 2
    assert result["missed_eligible_events"] == 1
    assert result["observed_early_rate"] == 1 / 3
    assert result["theoretical_max_early_rate"] == 2 / 3
    assert result["excluded_count"] == 1
    assert sum(row["events"] for row in result["histogram"]) == 3
    empty = opportunity_breakdown([case(None, None)])
    assert empty["observed_early_rate"] is None
    assert empty["theoretical_max_early_rate"] is None
    assert empty["eligible_detection_rate"] is None


@pytest.mark.parametrize(
    "actual,predicted", [(0, None), (15, None), (None, 0), (None, 15)]
)
def test_opportunity_refuses_events_outside_verified_window(actual, predicted):
    with pytest.raises(ValueError, match="14-day window"):
        opportunity_breakdown([case(actual, predicted)])


def test_diagnostic_api_requires_complete_matching_summary_and_no_table_filters(
    pg, tmp_path
):
    _, sessions = pg
    _, parent, item = result_fixture(sessions)
    with sessions.begin() as session:
        base = session.get(Run, parent)
        attrs = {
            c.name: getattr(base, c.name)
            for c in Run.__table__.columns
            if c.name not in {"id", "created_at"}
        }
        attrs.update(
            kind="alert_replay",
            forecast_run_id=parent,
            request_key="diagnostic-fixture",
            result_summary={
                "alert_metrics": {
                    "early_numerator": 1,
                    "event_denominator": 1,
                    "excluded_count": 0,
                }
            },
        )
        run = Run(**attrs)
        session.add(run)
        session.flush()
        key = run.id
        session.add(
            Alert(
                run_id=key,
                window_origin=D,
                item_id=item,
                as_of_date=D,
                alert_type="depletion",
                state="early",
                predicted_depletion_date=D + timedelta(days=8),
                actual_depletion_date=D + timedelta(days=9),
                is_evaluable=True,
                evaluation_class="TP",
                explanation={},
            )
        )
    with TestClient(create_app(settings(tmp_path))) as client:
        path = f"/api/v1/runs/{key}/alert-opportunities"
        result = client.get(path)
        assert result.status_code == 200, result.text
        assert result.json()["context"]["run_id"] == str(key)
        assert result.json()["diagnostic"]["theoretical_max_early_rate"] == 1
        assert client.get(path + "?item_id=1").status_code == 422
        assert (
            client.get(f"/api/v1/runs/{parent}/alert-opportunities").status_code == 409
        )
        with sessions.begin() as session:
            session.get(Run, key).result_summary = {
                "alert_metrics": {
                    "early_numerator": 0,
                    "event_denominator": 1,
                    "excluded_count": 0,
                }
            }
        assert client.get(path).status_code == 409
        with sessions.begin() as session:
            session.get(Run, key).status = "failed"
        assert client.get(path).status_code == 409
