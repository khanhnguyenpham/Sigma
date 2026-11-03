"""Synthetic total-30 boundary, provenance and HTTP/CSV checks; no source data."""

import json
from datetime import date
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from core.errors import DomainError
from main import create_app
from modules.reporting import monthly
from core.hashes import digest
from test_postgres_api import settings


def test_labels_are_next_30_not_current_day_or_calendar_month():
    daily = pd.DataFrame(
        dict(
            date=pd.date_range("2025-01-01", periods=61).strftime("%Y-%m-%d"),
            sales_qty=np.arange(61),
        )
    )
    actual = monthly.monthly_labels(daily, ["2025-01-01", "2025-01-31", "2025-02-01"])
    assert actual[0] == sum(range(1, 31))
    assert actual[1] == sum(range(31, 61))
    assert np.isnan(actual[2])  # D+30 beyond snapshot, never zero-fill.
    daily.loc[20, "sales_qty"] = np.nan
    assert np.isnan(monthly.monthly_labels(daily, ["2025-01-01"])[0])


def test_metrics_exclude_partial_split_windows_but_keep_actual_zero():
    f = pd.DataFrame(
        [
            dict(
                destination_country="A",
                carrier="B",
                split="test",
                model="demo",
                as_of_date="2025-09-30",
                actual_qty=0.0,
                forecast_qty=10.0,
                metric_eligible=True,
                is_top10=True,
            ),
            dict(
                destination_country="A",
                carrier="B",
                split="test",
                model="demo",
                as_of_date="2025-10-01",
                actual_qty=100.0,
                forecast_qty=90.0,
                metric_eligible=True,
                is_top10=True,
            ),
            dict(
                destination_country="A",
                carrier="B",
                split="test",
                model="demo",
                as_of_date="2025-12-30",
                actual_qty=1.0,
                forecast_qty=999.0,
                metric_eligible=False,
                is_top10=True,
            ),
        ]
    )
    m = monthly.evaluate_predictions(f).iloc[0]
    assert m.n_scored_pairs == 2 and m.n_positive_pairs == 1
    assert m.mape_positive_pct == 10 and m.mae == 10 and m.bias == 0
    assert m.coverage == 1
    summary = monthly.benchmark_summary(
        monthly.evaluate_predictions(f), pd.DataFrame(columns=["model"])
    )
    assert summary["routes_below_20_pct"] == 1 and not summary["meets_r05"]


def write_package(cfg, source):
    forecasts = pd.DataFrame(
        [
            dict(
                destination_country="DemoLand",
                carrier="DemoCarrier",
                model="=formula",
                split="test",
                as_of_date="2025-09-30",
                window_start="2025-10-01",
                target_date="2025-10-30",
                actual_qty=100.0,
                forecast_qty=90.0,
                metric_eligible=True,
                is_top10=True,
                window_days=30,
            ),
            dict(
                destination_country="DemoLand",
                carrier="DemoCarrier",
                model="=formula",
                split="future",
                as_of_date="2025-12-31",
                window_start="2026-01-01",
                target_date="2026-01-30",
                actual_qty=np.nan,
                forecast_qty=85.0,
                metric_eligible=False,
                is_top10=True,
                window_days=30,
            ),
        ]
    )
    frames = {
        "forecasts.csv": forecasts,
        "metrics.csv": monthly.evaluate_predictions(forecasts),
        "baselines.csv": pd.DataFrame([dict(model="Selected", mape_positive_pct=10)]),
    }
    payloads = {
        name: frame.to_csv(index=False).encode() for name, frame in frames.items()
    }
    manifest = dict(
        source_sha256=source.source_sha256,
        target_version=source.target_version,
        observation_end=str(source.observation_end),
        source_import_run_id=str(source.id),
        benchmark_run_id="synthetic-benchmark",
        summary_sha256="b" * 64,
        selection_sha256="c" * 64,
        acceptance=json.loads(monthly.ACCEPTANCE.read_bytes()),
        acceptance_sha256=monthly.sha(monthly.ACCEPTANCE.read_bytes()),
        evaluation_limit="Synthetic retrospective fixture",
        inventory_relationship="H14 unchanged",
        verified_at_utc="2026-10-20T00:00:00Z",
        files={name: monthly.sha(data) for name, data in payloads.items()},
    )
    key = digest(manifest)
    folder = monthly.package_root(cfg) / key
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name, data in payloads.items():
        (folder / name).write_bytes(data)
    (folder.parent / (monthly.source_key(source) + ".json")).write_text(
        json.dumps(dict(package_id=key)), encoding="utf-8"
    )
    return folder


@pytest.mark.parametrize("tamper", ["payload", "manifest", "acceptance", "target"])
def test_package_rejects_changed_bytes_or_context(tmp_path, monkeypatch, tamper):
    cfg = SimpleNamespace(output_root=tmp_path / "runs")
    source = SimpleNamespace(
        id="synthetic",
        source_sha256="a" * 64,
        target_version="demo",
        observation_end=date(2025, 12, 31),
    )
    folder = write_package(cfg, source)
    if tamper == "payload":
        (folder / "metrics.csv").write_text("changed")
    elif tamper == "manifest":
        manifest = json.loads((folder / "manifest.json").read_bytes())
        manifest["target_version"] = "changed"
        (folder / "manifest.json").write_text(json.dumps(manifest))
    elif tamper == "acceptance":
        changed = tmp_path / "acceptance.json"
        changed.write_text("{}")
        monkeypatch.setattr(monthly, "ACCEPTANCE", changed)
    else:
        source.target_version = "other-target"
    with pytest.raises(DomainError):
        monthly.load_package(cfg, source)


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


def test_receipt_path_and_missing_benchmark_are_not_served(tmp_path):
    cfg = SimpleNamespace(output_root=tmp_path / "runs", source_root=tmp_path)
    with pytest.raises(DomainError):
        monthly.verified_bundle(cfg, "../receipt.json")
    source = SimpleNamespace(
        source_sha256="a" * 64,
        target_version="demo",
        observation_end=date(2025, 12, 31),
    )
    with pytest.raises(DomainError, match="Prepare the verified"):
        monthly.load_package(cfg, source)
