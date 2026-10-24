"""Validation-only daily experiment. Never changes M2 or serving selections."""

import argparse
import hashlib
import json
import platform
import uuid
from importlib.metadata import version
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sqlalchemy import text
from sigma_m3.core.db import database
from sigma_m3.core.settings import Settings
from sigma_m3.core.run_context import required_run, source_data_id
from sigma_m3.core.hashes import digest
from sigma_m3.services.forecast import clean_json
from src.evaluation import score

ROUTE = ["destination_country", "carrier"]
PROTOCOL = {
    "id": "daily-validation-v1",
    "target": "A08_success_order_datetime_UTC_quantity",
    "train_end": "2025-06-30",
    "validation_end": "2025-09-30",
    "test_access": False,
    "horizon": 14,
    "selection_block": "h1-7",
    "refit_days": 7,
    "rolling_train_days": 365,
    "minimum_history": 90,
    "seed": 42,
    "candidates": [
        "last",
        "seasonal7",
        "mean28",
        "mean90",
        "mape_median90",
        "weekday_median90",
        "lgbm_poisson",
        "lgbm_weighted_l1",
    ],
    "lgbm": {
        "n_estimators": 150,
        "learning_rate": 0.03,
        "num_leaves": 15,
        "min_child_samples": 100,
        "reg_lambda": 10,
        "n_jobs": 2,
        "random_state": 42,
        "deterministic": True,
        "force_col_wise": True,
        "verbosity": -1,
    },
}


def weighted_median(values):
    """Positive MAPE's empirical minimizer; zeros remain in evaluation."""
    positive = np.sort(np.asarray(values, dtype=float))
    positive = positive[positive > 0]
    if not len(positive):
        return 0.0
    weights = 1 / positive
    return float(positive[np.searchsorted(np.cumsum(weights), weights.sum() / 2)])


def examples(daily):
    """Every feature is constructed from the prefix ending at its origin."""
    rows = []
    for route_id, (key, part) in enumerate(daily.groupby(ROUTE, sort=True)):
        part = part.sort_values("date")
        dates = pd.DatetimeIndex(part.date)
        values = part.sales_qty.to_numpy(float)
        if (
            dates.has_duplicates
            or not dates.equals(pd.date_range("2024-01-01", PROTOCOL["validation_end"]))
            or not np.isfinite(values).all()
            or (values < 0).any()
            or not part.actual_available.eq(True).all()
        ):
            raise ValueError(
                "Daily experiment requires complete observed calendar data"
            )
        for pos in range(89, len(dates) - 1):
            past = values[: pos + 1]
            origin = dates[pos]
            week = {
                weekday: float(
                    np.median(
                        past[-90:][dates[pos - 89 : pos + 1].dayofweek == weekday]
                    )
                )
                for weekday in range(7)
            }
            base = dict(
                destination_country=key[0],
                carrier=key[1],
                route_id=route_id,
                as_of_date=origin,
                lag1=past[-1],
                lag7=past[-7],
                lag14=past[-14],
                lag28=past[-28],
                mean7=past[-7:].mean(),
                mean28=past[-28:].mean(),
                mean90=past[-90:].mean(),
                std7=past[-7:].std(),
                std28=past[-28:].std(),
                std90=past[-90:].std(),
                mape_median90=weighted_median(past[-90:]),
            )
            for horizon in range(1, min(14, len(dates) - 1 - pos) + 1):
                target = dates[pos + horizon]
                rows.append(
                    {
                        **base,
                        "target_date": target,
                        "horizon": horizon,
                        "target_weekday": target.dayofweek,
                        "target_month": target.month,
                        "trend_day": (target - dates[0]).days,
                        "actual_qty": values[pos + horizon],
                        "last": past[-1],
                        "seasonal7": past[-7 + ((horizon - 1) % 7)],
                        "weekday_median90": week[target.dayofweek],
                    }
                )
    return pd.DataFrame(rows)


FEATURES = [
    "route_id",
    "horizon",
    "target_weekday",
    "target_month",
    "trend_day",
    "lag1",
    "lag7",
    "lag14",
    "lag28",
    "mean7",
    "mean28",
    "mean90",
    "std7",
    "std28",
    "std90",
    "weekday_median90",
]


def fit_rows(frame, cutoff):
    return frame.loc[
        frame.target_date.le(cutoff)
        & frame.as_of_date.ge(cutoff - pd.Timedelta(days=365))
        & frame.as_of_date.lt(cutoff)
    ]


def evaluate(daily):
    return evaluate_frame(examples(daily), FEATURES, PROTOCOL)


def evaluate_frame(frame, features, protocol):
    """Shared validation evaluator; serving models never call this function."""
    if {"actual_qty", "forecast_qty"} & set(features):
        raise ValueError("Target values cannot be model features")
    end = pd.Timestamp(protocol["validation_end"])
    if (
        frame.target_date.gt(end).any()
        or not np.isfinite(frame.actual_qty).all()
        or frame.actual_qty.lt(0).any()
        or ((frame.target_date - frame.as_of_date).dt.days != frame.horizon).any()
    ):
        raise ValueError("Invalid labels or targets beyond the validation boundary")
    start = pd.Timestamp(protocol["train_end"])
    validation = frame.loc[frame.as_of_date.ge(start)].copy()
    output, fit_log = [], []
    for model in protocol["candidates"]:
        forecasts = validation[
            ROUTE + ["as_of_date", "target_date", "horizon", "actual_qty"]
        ].copy()
        forecasts["model"] = model
        if not model.startswith("lgbm_"):
            forecasts["forecast_qty"] = validation[model].to_numpy()
        else:
            forecasts["forecast_qty"] = np.nan
            for cutoff in pd.date_range(
                start, protocol["validation_end"], freq=f"{protocol['refit_days']}D"
            ):
                fold_mask = validation.as_of_date.ge(cutoff) & validation.as_of_date.lt(
                    cutoff + pd.Timedelta(days=protocol["refit_days"])
                )
                scopes = (
                    sorted(validation.route_id.unique())
                    if model in protocol.get("route_specific", [])
                    else [None]
                )
                for route_id in scopes:
                    mask = (
                        fold_mask
                        if route_id is None
                        else fold_mask & validation.route_id.eq(route_id)
                    )
                    if not mask.any():
                        continue
                    train = fit_rows(frame, cutoff)
                    if route_id is not None:
                        train = train.loc[train.route_id.eq(route_id)]
                    objective = protocol.get("objectives", {}).get(
                        model, "poisson" if model == "lgbm_poisson" else "regression_l1"
                    )
                    parameters = protocol.get("parameters", {}).get(
                        model, protocol["lgbm"]
                    )
                    estimator = LGBMRegressor(**parameters, objective=objective)
                    weights = (
                        None
                        if objective == "poisson"
                        else 1 / np.maximum(train.actual_qty.to_numpy(), 1)
                    )
                    fit_options = (
                        {"categorical_feature": protocol["categorical_features"]}
                        if protocol.get("categorical_features")
                        else {}
                    )
                    estimator.fit(
                        train[features],
                        train.actual_qty,
                        sample_weight=weights,
                        **fit_options,
                    )
                    predicted = estimator.predict(validation.loc[mask, features])
                    forecasts.loc[mask, "forecast_qty"] = np.maximum(0, predicted)
                    fit_log.append(
                        dict(
                            model=model,
                            route_id=None if route_id is None else int(route_id),
                            fit_cutoff=cutoff.date().isoformat(),
                            max_label_end=train.target_date.max().date().isoformat(),
                            training_pairs=len(train),
                            predicted_pairs=int(mask.sum()),
                            negative_clipped=int((predicted < 0).sum()),
                        )
                    )
        output.append(forecasts)
    predictions = pd.concat(output, ignore_index=True)
    records = []
    for (country, carrier, model), group in predictions.groupby(ROUTE + ["model"]):
        for block in (1, 2):
            subset = group.loc[group.horizon.between(1 + 7 * (block - 1), 7 * block)]
            records.append(
                dict(
                    destination_country=country,
                    carrier=carrier,
                    model=model,
                    block=block,
                    split="validation",
                    **score(subset),
                )
            )
    metrics = pd.DataFrame(records)
    candidates = metrics.loc[(metrics.block == 1) & metrics.coverage.eq(1)].copy()
    selected = candidates.sort_values(
        ROUTE + ["mape_positive_pct", "mae", "model"], kind="stable"
    ).drop_duplicates(ROUTE)
    return predictions, metrics, selected, fit_log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=uuid.UUID, required=True)
    args = parser.parse_args()
    settings = Settings.from_env()
    root = Path(__file__).resolve().parents[2]
    output = root / "outputs/research" / (PROTOCOL["id"] + "-" + str(uuid.uuid4()))
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        status="planned",
        protocol=PROTOCOL,
        protocol_sha256=digest(PROTOCOL),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        created_at=datetime.now(timezone.utc).isoformat(),
        evaluation_limit="Validation experiment only; no test read or serving replacement.",
        runtime={
            "python": platform.python_version(),
            "packages": {
                name: version(name)
                for name in ["lightgbm", "numpy", "pandas", "scikit-learn"]
            },
        },
        requirements_sha256={
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ["requirements.txt", "M3/backend/requirements.txt"]
        },
    )

    def save():
        (output / "manifest.json").write_text(
            json.dumps(clean_json(manifest), indent=2), encoding="utf-8"
        )

    save()
    engine, sessions = database(settings.database_url)
    try:
        with sessions() as session:
            source = required_run(
                session, args.source_run, "source_import", complete=True
            )
            manifest.update(
                source_run_id=str(source.id), source_sha256=source.source_sha256
            )
            daily = pd.read_sql(
                text("""
                SELECT w.destination_country,w.carrier,d.date,
                       sum(d.sales_qty) AS sales_qty,
                       bool_and(d.actual_available) AS actual_available
                FROM daily_sales d JOIN items i ON i.id=d.item_id
                JOIN warehouses w ON w.id=i.warehouse_id
                WHERE d.source_import_run_id=:source AND d.date<=:end
                GROUP BY w.destination_country,w.carrier,d.date
            """),
                session.connection(),
                params={
                    "source": source_data_id(source),
                    "end": PROTOCOL["validation_end"],
                },
                parse_dates=["date"],
            )
        # Rank by TRAIN quantity, independently of the registered final selection.
        ranking = (
            daily.loc[daily.date.le(PROTOCOL["train_end"])]
            .groupby(ROUTE)
            .sales_qty.sum()
            .sort_values(ascending=False, kind="stable")
        )
        top = set(ranking.head(10).index)
        registered = json.loads(
            (root / "data/configs/m2-final.json").read_text(encoding="utf-8")
        )
        assert top == {
            (r["destination_country"], r["carrier"]) for r in registered["routes"]
        }
        daily = daily.loc[
            [tuple(k) in top for k in daily[ROUTE].itertuples(index=False, name=None)]
        ]
        daily = daily.sort_values(ROUTE + ["date"]).reset_index(drop=True)
        manifest.update(
            observed_end=daily.date.max().date().isoformat(),
            observed_rows=len(daily),
            observed_data_sha256=hashlib.sha256(
                pd.util.hash_pandas_object(daily, index=False).values.tobytes()
            ).hexdigest(),
        )
        manifest["status"] = "running"
        save()
        forecasts, metrics, selected, fit_log = evaluate(daily)
        assert len(selected) == 10 and metrics.coverage.eq(1).all()
        assert all(r["max_label_end"] <= r["fit_cutoff"] for r in fit_log)
        forecasts.to_csv(output / "validation_predictions.csv", index=False)
        metrics.to_csv(output / "validation_metrics.csv", index=False)
        selected.to_csv(output / "validation_selection.csv", index=False)
        (output / "fit_log.json").write_text(
            json.dumps(fit_log, indent=2), encoding="utf-8"
        )
        manifest.update(
            status="complete",
            selection_sha256=digest(clean_json(selected.to_dict("records"))),
            routes=10,
            candidates=8,
            prediction_pairs=len(forecasts),
            fits=len(fit_log),
            selected_mean_mape=float(selected.mape_positive_pct.mean()),
            routes_at_most20=int(selected.mape_positive_pct.le(20).sum()),
            artifacts={
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in output.iterdir()
                if p.name != "manifest.json"
            },
        )
        save()
        print(
            json.dumps(
                {
                    "output": str(output),
                    **{
                        k: manifest[k]
                        for k in [
                            "status",
                            "routes_at_most20",
                            "selected_mean_mape",
                            "fits",
                        ]
                    },
                }
            )
        )
    except Exception:
        manifest["status"] = "failed"
        save()
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
