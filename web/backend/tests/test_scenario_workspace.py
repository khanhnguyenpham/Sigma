"""Scenario history filters and public frozen settings, on synthetic test data only."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from main import create_app
from modules.configuration.models import Scenario
from modules.runs.models import Run
from test_postgres_api import D, settings


def test_history_filters_before_count_and_page_and_keeps_frozen_settings(pg, tmp_path):
    _, sessions = pg
    with sessions.begin() as session:
        scenarios = [Scenario(code=code, name=code, version=1, description="synthetic",
                              settings={}, assumption_version="synthetic") for code in ("base", "other")]
        session.add_all(scenarios)
        session.flush()
        base, other = (row.id for row in scenarios)
        rows = []
        for index, (scenario_id, kind, status) in enumerate([
            (base, "stock_projection", "complete"), (base, "stock_projection", "complete"),
            (base, "stock_projection", "complete"), (base, "stock_projection", "failed"),
            (other, "stock_projection", "complete"), (None, "forecast", "complete"),
        ]):
            row = Run(kind=kind, status=status, scenario_id=scenario_id, as_of_date=D, observation_end=D,
                      target_version="synthetic", config_version="synthetic", assumption_version="synthetic",
                      code_revision="synthetic", code_sha256="a" * 64, config_sha256="b" * 64,
                      request_key=f"history-{index}", request_sha256="c" * 64,
                      created_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index),
                      config_snapshot={"private_path": "/private/synthetic", "scenario": {
                          "name": "Frozen name", "version": 7, "settings": {"cover_days": 14,
                              "safety_multiplier": 1.5, "private_path": "/private/settings"}}},
                      result_summary={"origins": 185, "audit": {"private": True}, "metrics": {}})
            session.add(row)
            session.flush()
            rows.append(str(row.id))
    with TestClient(create_app(settings(tmp_path))) as client:
        url = f"/api/v1/runs?scenario_id={base}&kind=stock_projection&status=complete&page_size=2"
        first = client.get(url).json()
        second = client.get(url + "&page=2").json()
        assert first["total"] == second["total"] == 3
        assert [r["id"] for r in first["items"] + second["items"]] == list(reversed(rows[:3]))
        assert client.get(f"/api/v1/runs?scenario_id={other}").json()["total"] == 1
        assert client.get("/api/v1/runs?kind=forecast&status=complete").json()["total"] == 1
        assert client.get(url.replace("status=complete", "status=failed")).json()["total"] == 1
        row = first["items"][0]
        assert row["scenario_name"] == "Frozen name" and row["scenario_version"] == 7
        assert "scenario_settings" not in row
        assert "audit" not in row["result_summary"] and "metrics" not in row["result_summary"]
        assert "config_snapshot" not in row and "private_path" not in str(row)
        detail = client.get(f"/api/v1/runs/{row['id']}").json()
        assert detail["scenario_settings"] == {"cover_days": 14, "safety_multiplier": 1.5}
        assert "private_path" not in str(detail)
        for invalid in ("scenario_id=0", "kind=unsupported", "status=unknown"):
            assert client.get("/api/v1/runs?" + invalid).status_code == 422
