"""Total-30 (R05 research) stays out of the application; its package module was removed in M5."""

import pytest
from fastapi.testclient import TestClient
from main import create_app
from test_postgres_api import settings


@pytest.mark.parametrize("mode", ["local", "demo"])
def test_monthly_removed_from_application(pg, tmp_path, mode):
    from dataclasses import replace
    cfg = replace(settings(tmp_path), mode=mode)
    with TestClient(create_app(cfg)) as client:
        assert not any("monthly" in path for path in client.get("/openapi.json").json()["paths"])
        for suffix in ("monthly-summary", "monthly-forecasts", "monthly-metrics",
                       "exports/monthly_forecasts", "exports/monthly_metrics"):
            response = client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000/" + suffix)
            assert response.status_code == 404
