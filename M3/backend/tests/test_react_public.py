"""Synthetic Streamlit React read models, isolation, versioning and forward plans."""

from datetime import date, timedelta
import gzip, io, json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "streamlit"))
from sigma_public import runtime
from sigma_public.react_api.bundle import PublicBundle
from sigma_public.react_api.dispatcher import PublicWorkspace


def fake_bundle(folder):
    folder.mkdir()
    catalog = pd.DataFrame(
        [
            dict(
                destination_country=f"Country{i // 20:02}",
                carrier=f"Carrier{i // 20:02}",
                sku=f"PACK-{i % 20:02}",
                product_type="eSIM",
                first_seen_date="2024-01-01",
                item_key=i,
                configured_rop_floor=0,
                moq=5,
                safety_days=2,
                supplier=f"SUP-{i // 20 + 1:03}",
            )
            for i in range(920)
        ]
    )
    labels = {
        "weekly46": dict(
            run_id="forecast-public", origin="2025-12-31", kind="forecast"
        ),
        "policy_base": dict(
            run_id="policy-public", origin="2025-09-30", kind="policy_replay"
        ),
        "alert_base": dict(
            run_id="alert-public", origin="2025-09-30", kind="alert_replay"
        ),
        "snapshot_2025-10-31_pending": dict(
            run_id="snapshot-public", origin="2025-10-31", kind="stock_projection"
        ),
        "snapshot_2025-12-31": dict(
            run_id="future-public", origin="2025-12-31", kind="stock_projection"
        ),
    }
    for spec in labels.values():
        spec.update(config_sha256="a" * 64, code_sha256="b" * 64)
    inventory = []
    alerts = []
    for label, origin in [
        ("snapshot_2025-10-31_pending", "2025-10-31"),
        ("snapshot_2025-12-31", "2025-12-31"),
        ("policy_base", "2025-10-31"),
    ]:
        for i in range(920):
            inventory.append(
                dict(
                    run_label=label,
                    item_key=i,
                    date=origin,
                    opening_qty=7 if i == 0 else 10,
                    receipts_qty=0,
                    sales_qty=0,
                    fulfilled_qty=0,
                    shortage_qty=0,
                    closing_qty=7 if i == 0 else 10,
                    ss=2,
                    rop_forecast=9,
                    rop=20 if i == 0 else 9,
                    target_stock=21 if i == 0 else 10,
                    pending_qty=20 if i == 0 else 0,
                    inventory_position=27 if i == 0 else 10,
                    needs_replenishment=i == 0,
                    recommended_qty=0,
                    config_status="complete",
                )
            )
            projection = json.dumps(
                [
                    dict(
                        date=str(date.fromisoformat(origin) + timedelta(days=h)),
                        closing_forecast=1,
                        receipts_qty=0,
                    )
                    for h in range(1, 15)
                ]
            )
            alerts.append(
                dict(
                    run_label=label,
                    item_key=i,
                    as_of_date=origin,
                    alert_type="depletion",
                    state="not_within_horizon",
                    predicted_depletion_date=None,
                    actual_depletion_date=None,
                    lead_days=None,
                    is_evaluable=False,
                    evaluation_class=None,
                    exclusion_reason=None,
                    projection_json=projection,
                )
            )
    receipts = pd.DataFrame(
        [
            dict(
                run_label="snapshot_2025-10-31_pending",
                item_key=0,
                ordered_on="2025-10-28",
                eta="2025-11-04",
                ordered_qty=20,
                received_qty=20,
                status="received",
                is_initial=True,
            ),
            dict(
                run_label="snapshot_2025-10-31_pending",
                item_key=0,
                ordered_on="2025-11-02",
                eta="2025-11-09",
                ordered_qty=30,
                received_qty=30,
                status="received",
                is_initial=False,
            ),
        ]
    )
    metric = []
    monthly = []
    weekly = []
    actual = []
    baselines = []
    routes = (
        catalog[["destination_country", "carrier"]].drop_duplicates().to_dict("records")
    )
    for i, route in enumerate(routes):
        for cadence in ["daily_origins", "nonoverlapping_30d"]:
            metric.append(
                dict(
                    **route,
                    split="test",
                    cadence=cadence,
                    is_top10=i < 10,
                    mape_positive_pct=12.0,
                    coverage=1,
                    n_positive_pairs=63,
                    n_scored_pairs=63,
                    mae=1,
                    wape_pct=12,
                    bias=1,
                )
            )
        for origin in ["2025-10-31", "2025-12-31"]:
            monthly.append(
                dict(
                    **route,
                    as_of_date=origin,
                    window_start=str(date.fromisoformat(origin) + timedelta(days=1)),
                    target_date=str(date.fromisoformat(origin) + timedelta(days=30)),
                    forecast_qty=30.0,
                    actual_qty=30.0 if origin == "2025-10-31" else None,
                    metric_eligible=origin == "2025-10-31",
                    split="test" if origin == "2025-10-31" else "future",
                    is_top10=i < 10,
                    model="synthetic",
                )
            )
            for block in [1, 2]:
                weekly.append(
                    dict(
                        **route,
                        as_of_date=origin,
                        block=block,
                        window_start=str(
                            date.fromisoformat(origin)
                            + timedelta(days=(block - 1) * 7 + 1)
                        ),
                        target_date=str(
                            date.fromisoformat(origin) + timedelta(days=block * 7)
                        ),
                        forecast_qty=140.0,
                        actual_qty=140.0 if origin == "2025-10-31" else None,
                        model_id="synthetic",
                        family="fixture",
                        selection_basis="synthetic",
                    )
                )
        for h in range(1, 15):
            actual.append(
                dict(
                    **route,
                    date=str(date(2025, 10, 31) + timedelta(days=h)),
                    sales_qty=20,
                )
            )
        if i < 10:
            baselines.append(dict(**route, model="Selected", mape_positive_pct=12.0))
    frames = dict(
        catalog=catalog,
        inventory=pd.DataFrame(inventory),
        alerts=pd.DataFrame(alerts),
        receipts=receipts,
        monthly_forecasts=pd.DataFrame(monthly),
        monthly_metrics=pd.DataFrame(metric),
        weekly=pd.DataFrame(weekly),
        weekly_metrics=pd.DataFrame(
            [dict(**r, granularity="weekly", block=1) for r in metric]
        ),
        baselines=pd.DataFrame(baselines),
        route_daily=pd.DataFrame(actual),
        scenarios=pd.DataFrame([dict(name="base")]),
    )
    files = {}
    tables = {}
    for name, frame in frames.items():
        raw = gzip.compress(frame.to_csv(index=False).encode(), mtime=0)
        filename = name + ".csv.gz"
        (folder / filename).write_bytes(raw)
        files[filename] = runtime.sha(raw)
        tables[name] = dict(file=filename, columns=list(frame), rows=len(frame))
    binary = io.BytesIO()
    np.savez_compressed(
        binary,
        forecast=np.ones((2, 920, 14)),
        origins=np.array(["2025-10-31", "2025-12-31"]),
    )
    (folder / "item_forecasts.npz").write_bytes(binary.getvalue())
    files["item_forecasts.npz"] = runtime.sha(binary.getvalue())
    meta = dict(
        kind="sigma-m3-public-v1",
        version="synthetic-react",
        raw_orders_included=False,
        profile=dict(L=7, R=1, H=14),
        acceptance=dict(version="r05-sales-30d-v1"),
        tables=tables,
        files=files,
        runs=labels,
        source_sha256="c" * 64,
        target_version="fixture",
        observation_end="2025-12-31",
        prepared_at_utc="2026-01-01T00:00:00Z",
        alert_metrics={},
        alert_opportunities={},
        benchmark_package_id="synthetic",
    )
    raw = json.dumps(meta).encode()
    (folder / "manifest.json").write_bytes(raw)
    (folder / "manifest.sha256").write_text(runtime.sha(raw))
    return PublicBundle(folder)


@pytest.fixture
def bundle(tmp_path):
    return fake_bundle(tmp_path / "public")


def payload(api, path):
    reply = api.call(path)
    assert reply["ok"], reply
    return reply["data"]


def test_react_public_matches_context_and_as_of_receipts(bundle):
    api = PublicWorkspace(bundle)
    data = payload(
        api, "/runs/snapshot-public/purchasing?as_of_date=2025-10-31&view=incoming"
    )
    assert data["total"] == 1 and data["summary"]["pending_units"] == 20
    assert (
        data["items"][0]["received_qty"] == 0
        and data["items"][0]["status"] == "ordered"
    )
    future = payload(
        api, "/runs/snapshot-public/purchasing?as_of_date=2025-11-10&view=history"
    )
    assert (
        future["context"]["known_orders_through"] == "2025-10-31"
        and future["total"] == 1
    )
    assert not future["summary"]["inventory_available"]
    assert (
        payload(
            api,
            "/runs/snapshot-public/purchasing?as_of_date=2025-10-31&view=incoming&search=missing",
        )["total"]
        == 0
    )
    assert (
        payload(api, "/runs/snapshot-public/alerts?as_of_date=2025-10-31&item_id=1")[
            "items"
        ][0]["explanation"]["projection"][0]["date"]
        == "2025-11-01"
    )
    assert not next(
        r for r in payload(api, "/runs")["items"] if r["id"] == "alert-public"
    )["result_summary"]["inventory_available"]


def test_react_monthly_and_allocated_future_actuals_remain_null(bundle):
    api = PublicWorkspace(bundle)
    summary = payload(api, "/runs/snapshot-public/monthly-summary")["summary"]
    assert (
        summary["routes_below_20_pct"] == 10 and summary["mean_mape_positive_pct"] == 12
    )
    rows = payload(
        api,
        "/runs/future-public/monthly-forecasts?as_of_date=2025-12-31&top10_only=false",
    )["items"]
    assert len(rows) == 46 and all(r["actual_qty"] is None for r in rows)
    rows = payload(
        api,
        "/runs/future-public/forecasts/items?as_of_date=2025-12-31&aggregate=route_day&item_id=1",
    )["items"]
    assert len(rows) == 14 and all(r["actual_qty"] is None for r in rows)
    assert sum(r["forecast_qty"] for r in rows) == 14


def test_react_configuration_and_plan_are_isolated_and_idempotent(bundle):
    a, b = PublicWorkspace(bundle), PublicWorkspace(bundle)
    assert a.call(
        "/warehouses/1", "PATCH", dict(city="Assumed City", expected_version=1)
    )["ok"]
    assert payload(b, "/warehouses")["items"][0]["city"] == ""
    assert payload(a, "/warehouses?run_id=snapshot-public")["items"][0]["city"] == ""
    scenario = dict(
        name="Plan",
        code="plan",
        description="synthetic",
        settings=dict(
            cover_days=7,
            safety_multiplier=1,
            policy_overrides=[
                dict(item_id=1, configured_rop_floor=20, moq=10, safety_days=2)
            ],
            receipts_initial=[
                dict(
                    item_id=1,
                    lot_key="known-lot",
                    ordered_on="2025-10-28",
                    eta="2025-11-04",
                    quantity=20,
                )
            ],
            receipts_declared=True,
        ),
    )
    created = a.call("/scenarios", "POST", scenario)
    assert created["ok"], created
    body = dict(
        kind="stock_projection",
        as_of_date="2025-10-31",
        source_import_run_id="public-source",
        forecast_run_id="forecast-public",
        scenario_id=created["data"]["id"],
    )
    result = a.call("/runs", "POST", body, "synthetic-key")
    assert result["ok"], result
    ident = result["data"]["run_id"]
    inventory = payload(
        a, f"/runs/{ident}/inventory?date_from=2025-10-31&date_to=2025-10-31&item_id=1"
    )["items"][0]
    assert (
        inventory["closing_qty"],
        inventory["pending_qty"],
        inventory["inventory_position"],
        inventory["rop"],
        inventory["recommended_qty"],
    ) == (7, 20, 27, 20, 0)
    assert a.call("/runs", "POST", body, "synthetic-key")["data"]["run_id"] == ident
    assert (
        a.call("/runs", "POST", {**body, "as_of_date": "2025-12-31"}, "synthetic-key")[
            "status"
        ]
        == 409
    )
    assert len(a.state["runs"]) == 1 and not b.state["runs"]
    assert (
        payload(
            a,
            "/runs/snapshot-public/inventory?date_from=2025-10-31&date_to=2025-10-31&item_id=1",
        )["items"][0]["closing_qty"]
        == 7
    )
    assert (
        a.call("/warehouses/1", "PATCH", dict(city="stale", expected_version=1))[
            "status"
        ]
        == 409
    )


def test_react_rpc_rejects_external_paths_invalid_configuration_and_unknown_runs(
    bundle,
):
    api = PublicWorkspace(bundle)
    assert api.call("https://outside.invalid/runs")["status"] == 400
    assert api.call("/runs/../../secret")["status"] == 400
    assert api.call("/runs/unknown")["status"] == 404
    assert api.call("/warehouses?run_id=unknown")["status"] == 404
    assert (
        api.call("/runs/forecast-public/workspace?as_of_date=2025-10-31")["status"]
        == 409
    )
    assert api.call("/runs", "DELETE")["status"] == 400
    assert not api.call("/runs", "POST", dict(kind="forecast"), "synthetic-key")["ok"]
    assert not api.call("/runs/snapshot-public/purchasing?as_of_date=bad")["ok"]
    assert not api.call(
        "/runs/snapshot-public/purchasing?as_of_date=2025-10-31&search=" + "x" * 81
    )["ok"]
    count = len(api.state["scenarios"])
    assert not api.call(
        "/scenarios",
        "POST",
        dict(
            name="Bad", code="bad", settings=dict(cover_days=14, receipts_declared=True)
        ),
    )["ok"]
    for field in ["policy_overrides", "receipts_initial"]:
        settings = dict(cover_days=7, safety_multiplier=1, receipts_declared=True)
        settings[field] = [None]
        assert not api.call(
            "/scenarios", "POST", dict(name="Bad", code="bad", settings=settings)
        )["ok"]
    assert len(api.state["scenarios"]) == count


def test_react_public_export_respects_scope_and_escapes_formula(bundle):
    api = PublicWorkspace(bundle)
    reply = api.call(
        "/runs/snapshot-public/purchasing/export?as_of_date=2025-10-31&view=incoming&page=99&page_size=1"
    )
    assert reply["ok"]
    rows = list(__import__("csv").DictReader(io.StringIO(reply["csv"])))
    assert (
        len(rows) == 1
        and rows[0]["received_qty"] == "0"
        and rows[0]["known_orders_through"] == "2025-10-31"
    )
    from sigma_public.react_api.dispatcher import csv_text

    assert "'=formula" in csv_text(
        [dict(model="=formula", actual_qty=None)], dict(scope="test")
    )


def test_public_score_source_stays_identical_to_core():
    original = Path(__file__).resolve().parents[3] / "src/evaluation.py"
    public = Path(__file__).resolve().parents[2] / "streamlit/sigma_public/metrics.py"
    assert public.read_bytes() == original.read_bytes()


def test_projection_origin_choices_require_stock_and_forecast(bundle):
    forecast = next(r for r in bundle.runs if r["kind"] == "forecast")
    assert forecast["result_summary"]["stock_projection_origins"] == [
        "2025-10-31",
        "2025-12-31",
    ]
    for origin in bundle.stock_projection_origins:
        seed = bundle.seed_inventory(origin)
        assert len(seed) == 920 and origin in bundle.origin_index
    assert "2025-07-01" not in bundle.stock_projection_origins


def test_host_upgrade_discards_stale_commands_but_refresh_preserves_current_session(
    bundle,
):
    from sigma_public.react_host import workspace_for, ADAPTER_VERSION

    old = PublicWorkspace(bundle)
    state = dict(
        sigma_react_workspace=old,
        sigma_react_adapter_version="older",
        sigma_react_ui={"requests": [{"method": "POST", "path": "/runs"}]},
        sigma_react_responses={"stale": "cached"},
    )
    current = workspace_for(bundle, state)
    assert current is not old
    assert state["sigma_react_adapter_version"] == ADAPTER_VERSION
    assert "sigma_react_ui" not in state and "sigma_react_responses" not in state
    current.state["warehouses"][0]["city"] = "Session city"
    assert workspace_for(bundle, state) is current
    assert current.state["warehouses"][0]["city"] == "Session city"


def test_host_bundle_cache_is_keyed_by_adapter_revision(bundle, monkeypatch):
    import sigma_public.react_host as host

    calls = []

    def load(folder):
        calls.append(folder)
        return type("PinnedBundle", (), {"pin": bundle.pin})()

    monkeypatch.setattr(host, "PublicBundle", load)
    host.load_bundle.clear()
    first = host.load_bundle("synthetic-public-release", bundle.pin, "v1")
    assert host.load_bundle("synthetic-public-release", bundle.pin, "v1") is first
    assert host.load_bundle("synthetic-public-release", bundle.pin, "v2") is not first
    assert len(calls) == 2
    host.load_bundle.clear()
