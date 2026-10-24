"""Verified, immutable 30-day benchmark; independent of operational H14 runs.

The CLI imports a sealed research result, never fits or selects on test. HTTP
only reads a hash-bound private package for the selected run's source/target.
"""

import hashlib
import io
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sqlalchemy import select, func
from sigma_m3.core.errors import DomainError
from sigma_m3.models import DailySales
from sigma_m3.modules.catalog.models import Item
from sigma_m3.core.hashes import digest
from sigma_m3.core.run_context import required_run, source_data_id
from src.evaluation import score

ROUTE = ["destination_country", "carrier"]
BUNDLE = "sigma_aggregate_focus_20261018"
ACCEPTANCE = Path(__file__).resolve().parents[4] / "configs/acceptance-30d.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise DomainError("monthly_invalid", message, 409)


def read_csv(data):
    return pd.read_csv(io.BytesIO(data), float_precision="round_trip")


def package_root(settings):
    return settings.output_root.parent / "monthly_benchmarks"


def source_key(source):
    return digest(
        [source.source_sha256, source.target_version, str(source.observation_end)]
    )


def route_daily(session, source):
    """Frozen source route identities, not mutable warehouse descriptions."""
    warehouses = {w["id"]: w for w in source.config_snapshot["warehouse_snapshot"]}
    rows = session.execute(
        select(
            Item.warehouse_id,
            DailySales.date,
            func.sum(DailySales.sales_qty),
            func.bool_and(DailySales.actual_available),
        )
        .join(Item, Item.id == DailySales.item_id)
        .where(DailySales.source_import_run_id == source_data_id(source))
        .group_by(Item.warehouse_id, DailySales.date)
    ).all()
    return (
        pd.DataFrame(
            [
                {
                    **{k: warehouses[w][k] for k in ROUTE},
                    "date": str(day),
                    "sales_qty": float(qty) if available else np.nan,
                }
                for w, day, qty, available in rows
            ]
        )
        .sort_values(ROUTE + ["date"])
        .reset_index(drop=True)
    )


def monthly_labels(daily, origins):
    """D+1..D+30, strict 30 observed days; unknown remains NaN."""
    series = daily.set_index(pd.to_datetime(daily.date)).sales_qty.sort_index()
    require(not series.index.has_duplicates, "Duplicate route-day observations")
    grid = series.reindex(pd.date_range(series.index.min(), series.index.max()))
    totals = grid.rolling(30, min_periods=30).sum()
    return totals.reindex(pd.to_datetime(origins) + pd.Timedelta(days=30)).to_numpy()


def evaluate_predictions(predictions):
    output = []
    for (country, carrier, split, model), group in predictions.groupby(
        ROUTE + ["split", "model"]
    ):
        if split == "future":
            continue
        # Full windows only. Tail actuals may be known in the current snapshot,
        # but never enter validation/test metrics across the split boundary.
        eligible = group[group.metric_eligible].sort_values("as_of_date")
        for cadence, selected in [
            ("daily_origins", eligible),
            ("nonoverlapping_30d", eligible.iloc[::30]),
        ]:
            result = score(selected, expected_pairs=len(selected))
            result.update(
                destination_country=country,
                carrier=carrier,
                split=split,
                model=model,
                cadence=cadence,
                window_days=30,
                is_top10=bool(group.is_top10.iloc[0]),
            )
            result["passes_20_pct"] = bool(
                result["n_positive_pairs"] > 0
                and result["coverage"] == 1
                and result["mape_positive_pct"] <= 20
            )
            output.append(result)
    return pd.DataFrame(output)


def verified_bundle(settings, receipt_name):
    require(
        Path(receipt_name).name == receipt_name and receipt_name.endswith(".json"),
        "Receipt must be a local JSON basename",
    )
    folder = settings.source_root / "outputs" / BUNDLE
    summary_data = (folder / "summary.json").read_bytes()
    summary = json.loads(summary_data)
    receipt_data = (folder.parent / receipt_name).read_bytes()
    receipt = json.loads(receipt_data)
    require(
        summary.get("status") == "complete" and summary.get("run_id") == BUNDLE,
        "Monthly source run is not complete",
    )
    require(
        receipt.get("status") == "verified"
        and receipt.get("run_id") == BUNDLE
        and receipt.get("summary_sha256") == sha(summary_data)
        and receipt.get("top10_train_exact") is True
        and receipt.get("selection_locked_before_test") is True,
        "Independent verification receipt does not match bundle",
    )
    files = {}
    for name, checksum in summary["files"].items():
        require(Path(name).name == name, "Invalid sealed artifact path")
        files[name] = (folder / name).read_bytes()
        require(sha(files[name]) == checksum, "Sealed artifact checksum differs")
    protocol = json.loads(files["protocol.json"])
    require(
        protocol["source_sha256"] == summary["source_sha256"], "Source hashes differ"
    )
    for name, checksum in protocol["implementation_modules_sha256"].items():
        path = (settings.source_root / name).resolve()
        require(
            path.is_relative_to(settings.source_root.resolve()),
            "Invalid implementation path",
        )
        require(
            sha(path.read_bytes()) == checksum,
            "Research implementation checksum differs",
        )
    lock = json.loads(files["selection_lock.json"])
    started = json.loads(files["test_started.json"])
    require(
        lock["selection_sha256"]
        == sha(files["selected_models.csv"])
        == started["selection_sha256"]
        and lock["test_used_for_ranking"] is False,
        "Selection lock differs",
    )
    require(
        pd.Timestamp(lock["created_at_utc"]) < pd.Timestamp(started["started_at_utc"]),
        "Selection was not locked before test",
    )
    return summary, files, receipt, sha(receipt_data), sha(summary_data)


def prepare(settings, session, source_id, receipt_name):
    source = required_run(session, source_id, "source_import", complete=True)
    summary, files, receipt, receipt_sha, summary_sha = verified_bundle(
        settings, receipt_name
    )
    require(
        source.source_sha256 == summary["source_sha256"],
        "Source import does not match benchmark",
    )
    daily = route_daily(session, source)
    old = (
        read_csv(files["daily_sales.csv"])
        .sort_values(ROUTE + ["date"])
        .reset_index(drop=True)
    )
    require(
        len(daily) == len(old)
        and daily[ROUTE + ["date"]].equals(old[ROUTE + ["date"]])
        and np.array_equal(daily.sales_qty, old.sales_qty),
        "M3 route-day source differs",
    )
    require(
        set(old.target_definition_version) == {source.target_version},
        "Sales target versions differ",
    )
    totals = (
        daily[daily.date <= "2025-06-30"].groupby(ROUTE).sales_qty.sum().reset_index()
    )
    top = totals.sort_values(["sales_qty"] + ROUTE, ascending=[False, True, True]).head(
        10
    )
    top_set = set(map(tuple, top[ROUTE].to_numpy()))
    old_top = read_csv(files["top_routes.csv"])
    require(
        top_set == set(map(tuple, old_top[ROUTE].to_numpy())) and len(top_set) == 10,
        "Train-ranked top 10 differs",
    )
    choices = read_csv(files["selected_models.csv"])
    choices = choices[choices.window_days == 30]
    require(
        not choices.duplicated(ROUTE).any()
        and len(choices) == len(totals)
        and set(choices.selection_split) == {"validation"}
        and set(choices.selection_cutoff) == {"2025-09-30"},
        "Invalid monthly selection",
    )
    chunks = []
    for split, start, end in [
        ("validation", "2025-06-30", "2025-09-29"),
        ("test", "2025-09-30", "2025-12-30"),
        ("future", "2025-12-31", "2025-12-31"),
    ]:
        frame = read_csv(files[f"{split}_predictions.csv"])
        frame = frame[frame.window_days == 30].merge(
            choices[ROUTE + ["model"]], on=ROUTE + ["model"], validate="many_to_one"
        )
        expected = set(pd.date_range(start, end).strftime("%Y-%m-%d"))
        require(
            len(frame) == len(totals) * len(expected)
            and not frame.duplicated(ROUTE + ["as_of_date"]).any()
            and set(frame.split) == {split},
            "Monthly forecast grid is incomplete",
        )
        require(
            np.isfinite(frame.forecast_qty).all()
            and (frame.forecast_qty >= 0).all()
            and (
                pd.to_datetime(frame.fit_cutoff) <= pd.to_datetime(frame.as_of_date)
            ).all(),
            "Invalid monthly forecasts or fit cutoffs",
        )
        origin = pd.to_datetime(frame.as_of_date)
        require(
            (pd.to_datetime(frame.window_start) == origin + pd.Timedelta(days=1)).all()
            and (
                pd.to_datetime(frame.target_date) == origin + pd.Timedelta(days=30)
            ).all(),
            "Monthly window must be D+1..D+30",
        )
        frame["metric_eligible"] = False
        frame["is_top10"] = [tuple(r) in top_set for r in frame[ROUTE].to_numpy()]
        for route, indexes in frame.groupby(ROUTE).groups.items():
            group = frame.loc[indexes]
            require(
                set(group.as_of_date) == expected, "Monthly origins differ by route"
            )
            route_source = daily[
                (daily.destination_country == route[0]) & (daily.carrier == route[1])
            ]
            known = monthly_labels(route_source, group.as_of_date)
            split_end = "2025-09-30" if split == "validation" else "2025-12-31"
            eligible = (
                (group.target_date <= split_end).to_numpy()
                if split != "future"
                else np.zeros(len(group), dtype=bool)
            )
            sealed_actual = np.where(eligible, known, np.nan)
            require(
                np.array_equal(group.actual_qty, sealed_actual, equal_nan=True),
                "Monthly actual labels differ",
            )
            frame.loc[indexes, "actual_qty"] = known
            frame.loc[indexes, "metric_eligible"] = eligible
        chunks.append(frame)
    forecasts = pd.concat(chunks, ignore_index=True).sort_values(
        ["split"] + ROUTE + ["as_of_date"]
    )
    metrics = evaluate_predictions(forecasts)
    for split in ["validation", "test"]:
        old_metrics = read_csv(files[f"{split}_metrics.csv"])
        for _, row in metrics[
            (metrics.split == split) & (metrics.cadence == "daily_origins")
        ].iterrows():
            match = old_metrics[
                (old_metrics.window_days == 30)
                & (old_metrics.cadence == "daily_origins")
                & (old_metrics.destination_country == row.destination_country)
                & (old_metrics.carrier == row.carrier)
                & (old_metrics.model == row.model)
            ]
            require(
                len(match) == 1 and row.n_scored_pairs == 63 and row.coverage == 1,
                "Expected exactly 63 complete monthly windows per split",
            )
            for metric in ["mape_positive_pct", "mae", "wape_pct", "bias"]:
                require(
                    np.isclose(row[metric], match.iloc[0][metric], rtol=0, atol=1e-9),
                    "Recomputed monthly metric differs",
                )
    baseline_rows = []
    test = forecasts[
        (forecasts.split == "test") & forecasts.metric_eligible & forecasts.is_top10
    ]
    for name, history in [("Naive", 1), ("MA7", 7), ("MA28", 28), ("Selected", 0)]:
        for route, group in test.groupby(ROUTE):
            group = group.copy()
            series = (
                daily[
                    (daily.destination_country == route[0])
                    & (daily.carrier == route[1])
                ]
                .set_index("date")
                .sales_qty
            )
            if history:
                means = series.rolling(history, min_periods=history).mean()
                group["forecast_qty"] = means.reindex(group.as_of_date).to_numpy() * 30
            baseline_rows.append(
                dict(model=name, **dict(zip(ROUTE, route)), **score(group))
            )
    baselines = pd.DataFrame(baseline_rows)
    config_data = ACCEPTANCE.read_bytes()
    manifest = dict(
        version="monthly-benchmark-v1",
        benchmark_run_id=BUNDLE,
        source_sha256=source.source_sha256,
        target_version=source.target_version,
        observation_end=str(source.observation_end),
        source_import_run_id=str(source.id),
        summary_sha256=summary_sha,
        selection_sha256=sha(files["selected_models.csv"]),
        verifier_sha256=receipt_sha,
        verified_at_utc=receipt["verified_at_utc"],
        acceptance=json.loads(config_data),
        acceptance_sha256=sha(config_data),
        test_independent=False,
        evaluation_limit="Retrospective: focus followed previous test inspection; not an independent holdout.",
        inventory_relationship="Read-only R05 benchmark. Existing H14 inventory forecasts are unchanged.",
        prepared_at_utc=datetime.now(timezone.utc).isoformat(),
        files={},
    )
    payloads = {
        name: frame.to_csv(index=False).encode()
        for name, frame in [
            ("forecasts.csv", forecasts),
            ("metrics.csv", metrics),
            ("baselines.csv", baselines),
        ]
    }
    manifest["files"] = {name: sha(data) for name, data in payloads.items()}
    key = digest(manifest)
    folder = package_root(settings) / key
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        (folder / name).write_bytes(data)
    (folder / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pointer = package_root(settings) / (source_key(source) + ".json")
    temporary = pointer.with_suffix(".tmp")
    temporary.write_text(json.dumps({"package_id": key}), encoding="utf-8")
    temporary.replace(pointer)
    return dict(
        package_id=key,
        forecasts=len(forecasts),
        metrics=len(metrics),
        summary=benchmark_summary(metrics, baselines),
    )


def load_package(settings, source):
    pointer = package_root(settings) / (source_key(source) + ".json")
    if not pointer.is_file():
        raise DomainError(
            "monthly_not_prepared",
            "Prepare the verified 30-day benchmark for this source first",
            409,
        )
    try:
        key = json.loads(pointer.read_bytes())["package_id"]
        require(
            isinstance(key, str)
            and len(key) == 64
            and all(c in "0123456789abcdef" for c in key),
            "Invalid benchmark package key",
        )
        folder = package_root(settings) / key
        manifest = json.loads((folder / "manifest.json").read_bytes())
        require(
            digest(manifest) == key
            and manifest["acceptance_sha256"] == sha(ACCEPTANCE.read_bytes()),
            "Benchmark configuration checksum differs",
        )
        require(
            manifest["source_sha256"] == source.source_sha256
            and manifest["target_version"] == source.target_version
            and manifest["observation_end"] == str(source.observation_end),
            "Benchmark source context differs",
        )
        frames = {}
        for name in ["forecasts.csv", "metrics.csv", "baselines.csv"]:
            data = (folder / name).read_bytes()
            require(
                sha(data) == manifest["files"][name],
                "Benchmark artifact checksum differs",
            )
            frames[name] = read_csv(data)
        return key, manifest, frames
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise DomainError(
            "monthly_invalid", "Monthly benchmark package is incomplete or invalid", 409
        ) from exc


def benchmark_summary(metrics, baselines):
    top = metrics[
        (metrics.split == "test")
        & (metrics.cadence == "daily_origins")
        & metrics.is_top10
    ]
    valid = top[
        (top.n_positive_pairs > 0) & (top.coverage == 1) & (top.mape_positive_pct <= 20)
    ]
    comparison = [
        dict(
            model=name,
            mean_mape_positive_pct=float(g.mape_positive_pct.mean()),
            routes_below_20_pct=int((g.mape_positive_pct <= 20).sum()),
        )
        for name, g in baselines.groupby("model", sort=False)
    ]
    return dict(
        expected_top_routes=10,
        available_top_routes=len(top),
        routes_below_20_pct=len(valid),
        meets_r05=len(top) == 10 and len(valid) == 10,
        mean_mape_positive_pct=float(top.mape_positive_pct.mean()),
        minimum_coverage=float(top.coverage.min()),
        pairs_per_route=int(top.n_scored_pairs.min()) if len(top) else 0,
        window_days=30,
        cadence="daily_origins",
        test_independent=False,
        baselines=comparison,
    )
