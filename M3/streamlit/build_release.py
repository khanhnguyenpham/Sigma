"""Local-only export of an explicit aggregate allowlist. Never copies raw or DB.

Run with the M3 environment. Destination must be a new private staging folder.
Review and test its contents before the separately authorized public deployment.
"""

import argparse
from datetime import datetime, timezone
import gzip
import io
import json
from pathlib import Path
import shutil
import sys
import uuid
import numpy as np
import pandas as pd
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sigma_m3.db import database
from sigma_m3.models import (
    Run,
    ItemForecast,
    RouteForecast,
    InventoryDaily,
    Replenishment,
    Alert,
)
from sigma_m3.services.runs import required_run, code_digest
from sigma_m3.services.monthly import load_package, route_daily
from sigma_m3.api.results import metric_records, Filters
from sigma_m3.services.alerts import replay_metrics, opportunity_breakdown
from sigma_m3.settings import Settings
from sigma_public.runtime import TABLES, FORBIDDEN, sha

SOURCE = "96e77f53-fa7c-46be-987f-50e308920dba"
FORECAST = "7f7c53cb-4603-4e0a-b945-f43a9b57a715"
POLICY = "d8d8cf3b-58cc-44eb-94f4-c79661131b3f"
ALERT = "c20da6c2-2fa8-486f-a53f-3ab401682041"
SNAPSHOTS = {
    "309cc381-70cf-4e6a-9c1e-5b1220c49950": "snapshot_2025-10-31_pending",
    "4b63935f-bc0c-4b3d-8dec-426a9751aaa3": "snapshot_2025-12-31",
}


def read(session, model, run, columns):
    return pd.read_sql(
        select(*(getattr(model, c) for c in columns)).where(model.run_id == run.id),
        session.connection(),
    )


def export(destination, settings):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    release = destination / "release_m3"
    release.mkdir()
    engine, sessions = database(settings.database_url)
    try:
        with sessions() as session:
            source = required_run(
                session, uuid.UUID(SOURCE), "source_import", complete=True
            )
            forecast = required_run(
                session, uuid.UUID(FORECAST), "forecast", complete=True
            )
            policy = required_run(
                session, uuid.UUID(POLICY), "policy_replay", complete=True
            )
            alert = required_run(
                session, uuid.UUID(ALERT), "alert_replay", complete=True
            )
            runs = {"weekly46": forecast, "policy_base": policy, "alert_base": alert}
            runs.update(
                {
                    label: required_run(
                        session, uuid.UUID(key), "stock_projection", complete=True
                    )
                    for key, label in SNAPSHOTS.items()
                }
            )
            for run in runs.values():
                assert (
                    run.source_sha256 == source.source_sha256
                    and run.target_version == source.target_version
                )
                assert run.result_summary.get("phase") == "verified"
                for name, checksum in run.artifact_manifest.items():
                    assert Path(name).name == name
                    assert (
                        sha((settings.output_root / str(run.id) / name).read_bytes())
                        == checksum
                    )
            package_id, monthly, frames = load_package(settings, source)
            catalog = (
                pd.DataFrame(source.config_snapshot["catalog_snapshot"])
                .sort_values(["destination_country", "carrier", "sku", "product_type"])
                .reset_index(drop=True)
            )
            catalog["item_key"] = np.arange(len(catalog))
            keys = dict(zip(catalog.item_id, catalog.item_key))
            warehouse_routes = {
                w["id"]: {k: w[k] for k in ["destination_country", "carrier"]}
                for w in source.config_snapshot["warehouse_snapshot"]
            }
            policies = {p["item_id"]: p for p in policy.config_snapshot["policies"]}
            for col in ["configured_rop_floor", "moq", "safety_days"]:
                catalog[col] = [policies[i][col] for i in catalog.item_id]
            catalog["supplier"] = [
                f"SUP-{int(policies[i]['supplier_id']):03}" for i in catalog.item_id
            ]
            catalog = catalog.drop(columns="item_id")
            assert len(catalog) == 920 and len(keys) == 920
            tables = dict(catalog=catalog, route_daily=route_daily(session, source))
            tables.update(
                {
                    "monthly_forecasts": frames["forecasts.csv"],
                    "monthly_metrics": frames["metrics.csv"],
                    "baselines": frames["baselines.csv"],
                }
            )
            weekly = read(
                session,
                RouteForecast,
                forecast,
                [
                    "warehouse_id",
                    "as_of_date",
                    "block",
                    "window_start",
                    "target_date",
                    "forecast_qty",
                    "actual_qty",
                    "family",
                    "model_id",
                    "selection_basis",
                ],
            )
            for col in ["destination_country", "carrier"]:
                weekly[col] = [warehouse_routes[w][col] for w in weekly.warehouse_id]
            tables["weekly"] = weekly.drop(columns="warehouse_id")
            metrics = pd.DataFrame(
                metric_records(session, forecast, Filters(page_size=100))
            )
            tables["weekly_metrics"] = metrics.drop(
                columns=[c for c in ["warehouse_id", "is_top10"] if c in metrics]
            )
            # Restore the explicit train-ranked flag, independent of test metrics.
            top = set(
                map(
                    tuple,
                    frames["metrics.csv"]
                    .query("is_top10")[["destination_country", "carrier"]]
                    .drop_duplicates()
                    .to_numpy(),
                )
            )
            tables["weekly_metrics"]["is_top10"] = [
                tuple(r) in top
                for r in tables["weekly_metrics"][
                    ["destination_country", "carrier"]
                ].to_numpy()
            ]
            origins = np.array(
                sorted(weekly.as_of_date.astype(str).unique()), dtype="U10"
            )
            cube = np.zeros((len(origins), 920, 14), dtype=np.float64)
            counts = np.zeros(cube.shape, dtype=np.uint8)
            query = select(
                ItemForecast.as_of_date,
                ItemForecast.item_id,
                ItemForecast.horizon_day,
                ItemForecast.forecast_qty,
            ).where(ItemForecast.run_id == forecast.id)
            for chunk in pd.read_sql(query, session.connection(), chunksize=150000):
                x = np.searchsorted(origins, chunk.as_of_date.astype(str))
                y = chunk.item_id.map(keys).to_numpy(int)
                z = chunk.horizon_day.to_numpy(int) - 1
                assert (counts[x, y, z] == 0).all()
                cube[x, y, z] = chunk.forecast_qty
                counts[x, y, z] += 1
            assert counts.shape == (185, 920, 14) and (counts == 1).all()
            for route, items in catalog.groupby(["destination_country", "carrier"]):
                totals = (
                    cube[:, items.item_key, :]
                    .reshape(len(origins), len(items), 2, 7)
                    .sum(axis=(1, 3))
                )
                actual = weekly[
                    (weekly.destination_country == route[0])
                    & (weekly.carrier == route[1])
                ].copy()
                actual["as_of_date"] = actual.as_of_date.astype(str)
                actual = actual.pivot(
                    index="as_of_date", columns="block", values="forecast_qty"
                ).reindex(origins)
                assert np.allclose(totals, actual.to_numpy(), rtol=0, atol=1e-8)
            stream = io.BytesIO()
            np.savez_compressed(stream, forecast=cube, origins=origins)
            binary = stream.getvalue()
            (release / "item_forecasts.npz").write_bytes(binary)
            inventory_parts, receipts_parts, alert_parts = [], [], []
            ledger_cols = [
                "item_id",
                "date",
                "opening_qty",
                "receipts_qty",
                "sales_qty",
                "fulfilled_qty",
                "shortage_qty",
                "closing_qty",
                "ss",
                "rop_forecast",
                "rop",
                "target_stock",
                "pending_qty",
                "inventory_position",
                "needs_replenishment",
                "recommended_qty",
                "config_status",
            ]
            for label, run in runs.items():
                if run.kind not in {"policy_replay", "stock_projection"}:
                    continue
                ledger = read(session, InventoryDaily, run, ledger_cols)
                assert (
                    ledger.closing_qty
                    == ledger.opening_qty + ledger.receipts_qty - ledger.fulfilled_qty
                ).all()
                assert (
                    ledger.sales_qty == ledger.fulfilled_qty + ledger.shortage_qty
                ).all()
                assert (
                    ledger.inventory_position == ledger.closing_qty + ledger.pending_qty
                ).all()
                ledger["run_label"] = label
                ledger["item_key"] = ledger.item_id.map(keys)
                inventory_parts.append(ledger.drop(columns="item_id"))
                receipts = read(
                    session,
                    Replenishment,
                    run,
                    [
                        "item_id",
                        "ordered_on",
                        "eta",
                        "ordered_qty",
                        "received_qty",
                        "status",
                        "is_initial",
                    ],
                )
                assert (
                    pd.to_datetime(receipts.eta)
                    == pd.to_datetime(receipts.ordered_on) + pd.Timedelta(days=7)
                ).all()
                receipts["run_label"] = label
                receipts["item_key"] = receipts.item_id.map(keys)
                receipts_parts.append(receipts.drop(columns="item_id"))
                if run.kind == "policy_replay":
                    assert ledger.sales_qty.sum() == run.result_summary["sales_qty"]
                    assert (
                        ledger.shortage_qty.sum() == run.result_summary["shortage_qty"]
                    )
            for label in ["alert_base", *SNAPSHOTS.values()]:
                run = runs[label]
                data = read(
                    session,
                    Alert,
                    run,
                    [
                        "item_id",
                        "as_of_date",
                        "alert_type",
                        "state",
                        "predicted_depletion_date",
                        "actual_depletion_date",
                        "lead_days",
                        "is_evaluable",
                        "evaluation_class",
                        "exclusion_reason",
                    ],
                )
                if run.kind == "alert_replay":
                    data = data[data.alert_type == "depletion"].copy()
                data["item_key"] = data.item_id.map(keys)
                data["run_label"] = label
                alert_parts.append(data.drop(columns="item_id"))
            cases = alert_parts[0].to_dict("records")
            recalculated = replay_metrics(cases)
            assert recalculated == alert.result_summary["alert_metrics"]
            diagnostic = opportunity_breakdown(cases)
            tables["inventory"] = pd.concat(inventory_parts, ignore_index=True)
            tables["receipts"] = pd.concat(receipts_parts, ignore_index=True)
            tables["alerts"] = pd.concat(alert_parts, ignore_index=True)
            scenarios = []
            for run in session.scalars(
                select(Run).where(
                    Run.kind.in_(["policy_replay", "alert_replay"]),
                    Run.status == "complete",
                )
            ):
                required_run(session, run.id, complete=True)
                assert run.source_sha256 == source.source_sha256
                scenario = run.config_snapshot["scenario"]
                scenarios.append(
                    dict(
                        scenario=scenario["code"],
                        name=scenario["name"],
                        kind=run.kind,
                        cover_days=scenario["settings"]["cover_days"],
                        safety_multiplier=scenario["settings"]["safety_multiplier"],
                        **{
                            k: run.result_summary.get(k)
                            for k in [
                                "fill_rate",
                                "shortage_qty",
                                "mean_closing",
                                "order_count",
                            ]
                        },
                        **{
                            k: (run.result_summary.get("alert_metrics") or {}).get(k)
                            for k in [
                                "early_rate",
                                "precision",
                                "recall",
                                "event_denominator",
                            ]
                        },
                    )
                )
            tables["scenarios"] = pd.DataFrame(scenarios)
            assert set(tables) == TABLES
            meta = dict(
                kind="sigma-m3-public-v1",
                version="m3-public-20261020-v1",
                raw_orders_included=False,
                source_sha256=source.source_sha256,
                target_version=source.target_version,
                observation_end=str(source.observation_end),
                profile=dict(L=7, R=1, H=14),
                acceptance=monthly["acceptance"],
                benchmark_package_id=package_id,
                source_code_sha256=code_digest(),
                monthly_summary_sha256=monthly["summary_sha256"],
                test_independent=False,
                alert_metrics=recalculated,
                alert_opportunities=diagnostic,
                policy_metrics={
                    k: policy.result_summary[k]
                    for k in [
                        "fill_rate",
                        "sales_qty",
                        "fulfilled_qty",
                        "shortage_qty",
                        "order_count",
                        "mean_closing",
                    ]
                },
                runs={
                    label: dict(
                        run_id=str(run.id),
                        config_sha256=run.config_sha256,
                        code_sha256=run.code_sha256,
                        origin=str(run.as_of_date),
                        kind=run.kind,
                    )
                    for label, run in runs.items()
                },
                prepared_at_utc=datetime.now(timezone.utc).isoformat(),
                tables={},
                files={"item_forecasts.npz": sha(binary)},
            )
            for name, frame in tables.items():
                assert not FORBIDDEN & set(frame), name
                assert not any(c.endswith("_id") and c != "model_id" for c in frame), (
                    name,
                    list(frame),
                )
                data = gzip.compress(frame.to_csv(index=False).encode("utf-8"), mtime=0)
                filename = name + ".csv.gz"
                (release / filename).write_bytes(data)
                meta["files"][filename] = sha(data)
                meta["tables"][name] = dict(
                    file=filename, columns=list(frame), rows=len(frame)
                )
            manifest_bytes = json.dumps(
                meta, ensure_ascii=False, indent=2, allow_nan=False
            ).encode()
            (release / "manifest.json").write_bytes(manifest_bytes)
            (release / "manifest.sha256").write_text(
                sha(manifest_bytes), encoding="ascii"
            )
    finally:
        engine.dispose()
    shutil.copytree(
        Path(__file__).parent / "sigma_public",
        destination / "sigma_public",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in [
        "__init__.py",
        "errors.py",
        "services/inventory.py",
        "services/alerts.py",
    ]:
        path = destination / "sigma_m3" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "M3/backend/src/sigma_m3" / name, path)
    (destination / "streamlit_app.py").write_text(
        "from sigma_public.app import main\nmain()\n", encoding="utf-8"
    )
    (destination / "requirements.txt").write_text(
        "streamlit==1.65.0\npandas==3.0.6\nnumpy==2.5.3\naltair==6.3.0\n",
        encoding="utf-8",
    )
    return dict(
        status="prepared_not_published",
        manifest_sha256=sha(manifest_bytes),
        data_bytes=sum(p.stat().st_size for p in release.iterdir()),
        rows={k: len(v) for k, v in tables.items()},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.destination, Settings.from_env()), ensure_ascii=False))
