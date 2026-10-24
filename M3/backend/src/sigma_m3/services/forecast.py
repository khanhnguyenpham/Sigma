
"""Validation-locked ML extension, final10 replay and causal H14 allocation."""
from sigma_m3.core.run_context import source_data_id
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib, json
import numpy as np
import pandas as pd
from sqlalchemy import select
from sigma_m3.core.errors import DomainError
from sigma_m3.models import Run, DailySales
from sigma_m3.services import m2_adapter
from sigma_m3.services.allocation import allocate
from M2.models.families import metrics
from src.data import audit_orders, daily_sales, route_top
from src.common import ROUTE


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return value


def progress(sessions, key, phase, **counts):
    with sessions.begin() as s:
        row = s.get(Run, key)
        row.result_summary = {"phase": phase, **counts}


def select_new(validation, cfg, routes, models):
    if not validation.split.eq("validation").all():
        raise DomainError("invalid_selection", "Selection requires validation only")
    scored = metrics(validation, cfg)
    primary = scored.loc[scored.block.eq(1) & scored.cadence.eq("daily_origins")]
    selected = []
    for country, carrier in routes:
        eligible = []
        for family, model in models:
            group = validation.loc[
                validation.destination_country.eq(country)
                & validation.carrier.eq(carrier)
                & validation.family.eq(family)
                & validation.model.eq(model)
            ]
            expected = pd.MultiIndex.from_product(
                [
                    pd.date_range(
                        pd.Timestamp(cfg["validation_start"]) - pd.Timedelta(days=1),
                        pd.Timestamp(cfg["validation_end"]) - pd.Timedelta(days=1),
                    ),
                    [1, 2],
                ],
                names=["as_of_date", "block"],
            )
            pairs = pd.MultiIndex.from_frame(group[["as_of_date", "block"]])
            if not pairs.is_unique or not pairs.sort_values().equals(expected):
                continue
            metric = primary.loc[
                primary.destination_country.eq(country)
                & primary.carrier.eq(carrier)
                & primary.family.eq(family)
                & primary.model.eq(model)
            ]
            if len(metric) != 1:
                continue
            record = metric.iloc[0]
            if record.coverage != 1 or not np.isfinite(group.forecast_qty).all():
                continue
            eligible.append(
                (
                    record.mape_positive_pct
                    if pd.notna(record.mape_positive_pct)
                    else float("inf"),
                    record.mae,
                    model,
                    family,
                    record,
                )
            )
        if not eligible:
            raise DomainError(
                "no_valid_candidate",
                "A route has no fully covered validation candidate",
            )
        _, _, model, family, record = min(eligible, key=lambda row: row[:3])
        selected.append(
            dict(
                destination_country=country,
                carrier=carrier,
                family=family,
                model=model,
                selection_basis="validation_locked",
                validation_mape_positive_pct=clean_json(record.mape_positive_pct),
                validation_mae=float(record.mae),
            )
        )
    return selected, scored


def execute_jobs(daily, split, jobs, folder, label, callback):
    frames = []
    files = {}
    with ProcessPoolExecutor(max_workers=3) as pool:
        pending = {
            pool.submit(
                m2_adapter.candidate_job, daily, split, family, model, routes
            ): (family, model, index)
            for index, (family, model, routes) in enumerate(jobs)
        }
        for count, future in enumerate(as_completed(pending), 1):
            family, model, index = pending[future]
            frame, log = future.result()
            name = f"{label}_{index:03}_{family}_{model}"
            frame.to_csv(folder / f"{name}_predictions.csv", index=False)
            log.to_csv(folder / f"{name}_fitlog.csv", index=False)
            files[f"{name}_predictions.csv"] = hashlib.sha256(
                (folder / f"{name}_predictions.csv").read_bytes()
            ).hexdigest()
            files[f"{name}_fitlog.csv"] = hashlib.sha256(
                (folder / f"{name}_fitlog.csv").read_bytes()
            ).hexdigest()
            frames.append(frame)
            callback(count, len(pending))
    return pd.concat(frames, ignore_index=True), files


def forecast_run(settings, sessions, key):
    with sessions() as s:
        run = s.get(Run, key)
        source = s.get(Run, run.source_import_run_id)
        source_hash = source.source_sha256
        catalog = source.config_snapshot["catalog_snapshot"]
        warehouses = source.config_snapshot["warehouse_snapshot"]
        mode = run.config_snapshot["request"]["mode"]
        origin = run.as_of_date
        lock_parent = s.get(Run, run.forecast_run_id) if run.forecast_run_id else None
        previous = (
            lock_parent.config_snapshot.get("selections") if lock_parent else None
        )
        previous_specs = (
            lock_parent.config_snapshot.get("model_specs") if lock_parent else None
        )
    cfg, model_settings, final = m2_adapter.configuration()
    sales, audit = audit_orders(settings.order_source("orders_snapshot"), cfg)
    if (
        audit["source_sha256_before"] != source_hash
        or source_hash != final["source_sha256"]
    ):
        raise DomainError(
            "parent_mismatch", "Source must match the registered fixed M2 protocol"
        )
    daily = daily_sales(sales, cfg)
    full_daily = daily.copy()
    top = route_top(daily, cfg)
    fixed = {(r["destination_country"], r["carrier"]) for r in final["routes"]}
    if set(top[ROUTE].itertuples(index=False, name=None)) != fixed:
        raise DomainError("parent_mismatch", "Train top10 differs from fixed final M2")
    all_routes = sorted(set(daily[ROUTE].itertuples(index=False, name=None)))
    new = [r for r in all_routes if r not in fixed]
    if len(all_routes) != 46 or len(new) != 36:
        raise DomainError("catalog_mismatch", "Profile requires all 46 train routes")
    specs = m2_adapter.specs_fingerprint()
    if previous_specs is not None and specs != previous_specs:
        raise DomainError(
            "parent_mismatch", "Forecast parent model specifications changed"
        )
    folder = settings.output_root / str(key)
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {}
    frames = []
    model_pool = [
        ("LightGBM", name) for name in sorted(model_settings["models"]["LightGBM"])
    ] + [("Prophet", "prophet_annual3_weekly_w540")]
    if mode == "replay":
        if origin != pd.Timestamp(cfg["observation_end"]).date():
            raise DomainError(
                "invalid_input",
                "Full replay uses the declared observation end as cutoff",
            )
        jobs = [
            (family, model, new) for family, model in model_pool if family == "LightGBM"
        ]
        jobs += [("Prophet", "prophet_annual3_weekly_w540", [route]) for route in new]
        progress(sessions, key, "validation", completed_jobs=0, total_jobs=len(jobs))
        val, files = execute_jobs(
            daily,
            "validation",
            jobs,
            folder,
            "validation",
            lambda n, total: progress(
                sessions, key, "validation", completed_jobs=n, total_jobs=total
            ),
        )
        manifest.update(files)
        selections, validation_metrics = select_new(val, cfg, new, model_pool)
        validation_metrics.to_csv(
            folder / "validation_candidate_metrics.csv", index=False
        )
        # Persist the lock before any new-route test work is submitted.
        lock = dict(
            selections=selections,
            model_specs=specs,
            source_sha256=source_hash,
            locked_at=datetime.now(timezone.utc).isoformat(),
        )
        payload = json.dumps(
            clean_json(lock), sort_keys=True, indent=2, allow_nan=False
        ).encode()
        (folder / "selection_lock.json").write_bytes(payload)
        selection_hash = hashlib.sha256(payload).hexdigest()
        with sessions.begin() as s:
            row = s.get(Run, key)
            row.selection_sha256 = selection_hash
            row.config_snapshot = {
                **row.config_snapshot,
                "selections": selections,
                "model_specs": specs,
                "selection_locked_at": lock["locked_at"],
                "catalog_snapshot": catalog,
                "warehouse_snapshot": warehouses,
            }
        frames.append(
            val.loc[
                [
                    any(
                        r.destination_country == c["destination_country"]
                        and r.carrier == c["carrier"]
                        and r.model == c["model"]
                        and r.family == c["family"]
                        for c in selections
                    )
                    for r in val.itertuples()
                ]
            ]
        )
        splits = ["test", "future"]
    else:
        if previous is None:
            raise DomainError("parent_mismatch", "Missing selection lock")
        selections = previous
        selection_hash = lock_parent.selection_sha256
        daily = daily.loc[daily.date.le(pd.Timestamp(origin))].copy()
        splits = ["future"]
        with sessions.begin() as s:
            row = s.get(Run, key)
            row.selection_sha256 = selection_hash
            row.config_snapshot = {
                **row.config_snapshot,
                "selections": selections,
                "model_specs": specs,
                "catalog_snapshot": catalog,
                "warehouse_snapshot": warehouses,
            }
    for split in splits:
        jobs = []
        for family, model in model_pool:
            routes = [
                (r["destination_country"], r["carrier"])
                for r in selections
                if (r["family"], r["model"]) == (family, model)
            ]
            if not routes:
                continue
            jobs.extend(
                [(family, model, [r]) for r in routes]
                if family == "Prophet"
                else [(family, model, routes)]
            )
        progress(sessions, key, split, completed_jobs=0, total_jobs=len(jobs))
        selected, files = execute_jobs(
            daily,
            split,
            jobs,
            folder,
            split,
            lambda n, total: progress(
                sessions, key, split, completed_jobs=n, total_jobs=total
            ),
        )
        manifest.update(files)
        frames.append(selected)
    for split in ["validation", "test", "future"] if mode == "replay" else ["future"]:
        progress(sessions, key, "fixed_top10_replay", split=split)
        fixed_frame, logs = m2_adapter.top10(daily, split)
        fixed_frame.to_csv(folder / f"final10_{split}_predictions.csv", index=False)
        for label, log in logs.items():
            log.to_csv(folder / f"final10_{split}_{label}_fitlog.csv", index=False)
        frames.append(fixed_frame)
    predictions = pd.concat(frames, ignore_index=True).sort_values(
        ROUTE + ["as_of_date", "block"]
    )
    if (
        predictions.duplicated(ROUTE + ["as_of_date", "block"]).any()
        or not np.isfinite(predictions.forecast_qty).all()
    ):
        raise DomainError("forecast_incomplete", "Duplicate or missing route forecast")
    expected_origins = (
        list(pd.date_range("2025-06-30", "2025-12-31"))
        if mode == "replay"
        else [pd.Timestamp(origin)]
    )
    expected = len(expected_origins) * 46 * 2
    if len(predictions) != expected:
        raise DomainError(
            "forecast_incomplete", "Forecast does not cover every route/origin/block"
        )
    for route, part in predictions.groupby(ROUTE):
        observed = pd.MultiIndex.from_frame(part[["as_of_date", "block"]])
        expected_index = pd.MultiIndex.from_product(
            [expected_origins, [1, 2]], names=["as_of_date", "block"]
        )
        if not observed.sort_values().equals(expected_index):
            raise DomainError(
                "forecast_incomplete", "A route is missing a required origin"
            )
    result_metrics = []
    if mode == "replay":
        scored = metrics(predictions.loc[predictions.split.ne("future")], cfg)
        result_metrics = clean_json(scored.to_dict("records"))
        # Independent historical report parity at aggregate level; old private per-origin bundle is unavailable here.
        historical = pd.read_csv(
            m2_adapter.ROOT / "M2/reports/final_m2_20261011/test_metrics.csv",
            float_precision="round_trip",
        )
        chosen = scored.loc[
            scored.split.eq("test")
            & scored.apply(
                lambda row: (row.destination_country, row.carrier) in fixed, axis=1
            )
        ]
        merged = chosen.merge(
            historical,
            on=ROUTE + ["block", "cadence", "model"],
            suffixes=("_new", "_old"),
            validate="one_to_one",
        )
        if len(merged) != 40:
            raise DomainError(
                "final10_mismatch", "Fixed final report comparison is incomplete"
            )
        for field in ["mape_positive_pct", "mae", "wape_pct", "bias", "coverage"]:
            np.testing.assert_allclose(
                merged[field + "_new"],
                merged[field + "_old"],
                atol=1e-8,
                rtol=0,
                equal_nan=True,
            )
    route_id = {(w["destination_country"], w["carrier"]): w["id"] for w in warehouses}
    selection = {
        (r["destination_country"], r["carrier"]): r
        for r in selections + final["routes"]
    }
    # Route actuals use observation coverage. Evaluation above still respects each split end.
    observed = {
        route: part.set_index("date").sales_qty
        for route, part in full_daily.groupby(ROUTE)
    }
    with sessions.begin() as s:
        raw = s.connection().connection.driver_connection
        columns = [
            "run_id",
            "warehouse_id",
            "as_of_date",
            "block",
            "window_start",
            "target_date",
            "forecast_qty",
            "actual_qty",
            "actual_available",
            "family",
            "model_id",
            "selection_basis",
            "parent_bundle_sha256",
        ]
        with (
            raw.cursor() as cursor,
            cursor.copy(
                "COPY route_forecasts (" + ",".join(columns) + ") FROM STDIN"
            ) as copy,
        ):
            for r in predictions.itertuples():
                route = (r.destination_country, r.carrier)
                values = observed[route].loc[r.window_start : r.target_date]
                actual = float(values.sum()) if len(values) == 7 else None
                copy.write_row(
                    (
                        key,
                        route_id[route],
                        r.as_of_date.date(),
                        r.block,
                        r.window_start.date(),
                        r.target_date.date(),
                        float(r.forecast_qty),
                        actual,
                        actual is not None,
                        r.family,
                        r.model,
                        selection[route]["selection_basis"],
                        final["source_sha256"] if route in fixed else None,
                    )
                )
    progress(
        sessions,
        key,
        "allocation",
        completed_origins=0,
        total_origins=len(expected_origins),
    )
    with sessions() as s:
        item_daily = pd.read_sql(
            select(
                DailySales.item_id,
                DailySales.date,
                DailySales.sales_qty,
                DailySales.actual_available,
            ).where(DailySales.source_import_run_id == source_data_id(source)),
            s.connection(),
            parse_dates=["date"],
        )
    if not item_daily.actual_available.all():
        raise DomainError(
            "insufficient_history", "Source contains missing calendar coverage"
        )
    matrix = item_daily.pivot(index="date", columns="item_id", values="sales_qty")
    item_count = 0
    by_route = {
        route: [i for i in catalog if (i["destination_country"], i["carrier"]) == route]
        for route in all_routes
    }
    for idx, as_of in enumerate(expected_origins, 1):
        allocation_rows = []
        for route, items in by_route.items():
            group = predictions.loc[
                predictions.as_of_date.eq(as_of)
                & predictions.destination_country.eq(route[0])
                & predictions.carrier.eq(route[1])
            ].sort_values("block")
            allocated = allocate(
                matrix[[i["item_id"] for i in items]],
                {i["item_id"]: i["first_seen_date"] for i in items},
                as_of,
                group.forecast_qty.to_numpy(),
            )
            allocation_rows.extend(allocated.itertuples(index=False, name=None))
        with sessions.begin() as s:
            raw = s.connection().connection.driver_connection
            columns = [
                "run_id",
                "item_id",
                "as_of_date",
                "target_date",
                "horizon_day",
                "forecast_qty",
                "actual_qty",
                "actual_available",
                "item_share",
                "weekday_weight",
                "share_window_days",
                "allocation_basis",
            ]
            with (
                raw.cursor() as cursor,
                cursor.copy(
                    "COPY item_forecasts (" + ",".join(columns) + ") FROM STDIN"
                ) as copy,
            ):
                for (
                    item_id,
                    as_date,
                    target,
                    h,
                    f,
                    share,
                    weight,
                    window,
                    basis,
                ) in allocation_rows:
                    actual = (
                        int(matrix.at[target, item_id])
                        if target in matrix.index
                        else None
                    )
                    copy.write_row(
                        (
                            key,
                            item_id,
                            as_date.date(),
                            target.date(),
                            h,
                            f,
                            actual,
                            actual is not None,
                            share,
                            weight,
                            window,
                            basis,
                        )
                    )
                    item_count += 1
        if idx % 10 == 0:
            progress(
                sessions,
                key,
                "allocation",
                completed_origins=idx,
                total_origins=len(expected_origins),
            )
    predictions.to_csv(folder / "route_predictions.csv", index=False)
    if m2_adapter.specs_fingerprint() != specs:
        raise DomainError("code_mismatch", "Model source changed during forecasting")
    from src.common import sha256

    if sha256(settings.order_source("orders_snapshot")) != source_hash:
        raise DomainError("source_changed", "Source changed during forecasting")
    for path in folder.glob("*"):
        if path.is_file():
            manifest[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    with sessions.begin() as s:
        s.get(Run, key).artifact_manifest = manifest
    return dict(
        phase="verified",
        routes=46,
        new_routes=36,
        fixed_routes=10,
        route_forecast_rows=len(predictions),
        item_forecast_rows=item_count,
        origins=len(expected_origins),
        selection_sha256=selection_hash,
        metrics=result_metrics,
        selections=selections + final["routes"],
        historical_top10_metrics_checked=mode == "replay",
        historical_per_origin_reference_available=False,
        evaluation_limit="Retrospective; fixed LG U+ was test-selected. Daily R05 remains open.",
    )
