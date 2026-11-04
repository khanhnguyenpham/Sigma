"""Saved forecast origins follow the selected run's frozen parent."""
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from main import create_app
from modules.forecasting.models import RouteForecast
from modules.runs.models import Run
from test_postgres_api import D, settings
from test_workspace_api import workspace_fixture


def test_saved_origins_parent_missing_actual_and_no_writes(pg, tmp_path):
    _, sessions = pg
    key, parent, _ = workspace_fixture(sessions)
    with sessions.begin() as session:
        parent = session.get(Run, key).forecast_run_id
        first = session.scalar(select(RouteForecast).where(RouteForecast.run_id == parent))
        for day, block, actual in [(D, 2, 4), (D + timedelta(days=1), 1, 0), (D + timedelta(days=1), 2, None)]:
            session.add(RouteForecast(run_id=parent, warehouse_id=first.warehouse_id, as_of_date=day,
                block=block, window_start=day+timedelta(days=1+7*(block-1)), target_date=day+timedelta(days=7*block),
                forecast_qty=5, actual_qty=actual, actual_available=actual is not None,
                family="synthetic", model_id="fixture", selection_basis="injected_fixture"))
        run_ids = session.scalars(select(Run.id).order_by(Run.id)).all()
        source = session.get(Run, parent).source_import_run_id
    with TestClient(create_app(settings(tmp_path))) as client:
        path = f"/api/v1/runs/{key}/forecasts/origins"
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["context"]["run_id"] == str(parent)
        assert data["items"] == [dict(as_of_date=str(D), actual_available=True),
                                 dict(as_of_date=str(D+timedelta(days=1)), actual_available=False)]
        assert client.get(f"/api/v1/runs/{parent}/forecasts/origins").json() == data
        assert client.get(f"/api/v1/runs/{source}/forecasts/origins").status_code == 409
        with sessions.begin() as session:
            session.get(Run, source).status = "invalidated"
        assert client.get(path).status_code == 409
    with sessions() as session:
        assert session.scalars(select(Run.id).order_by(Run.id)).all() == run_ids
