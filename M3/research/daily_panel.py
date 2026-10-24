"""Causal counts, annual and market features; validation only, no serving changes."""

import argparse
import hashlib
import json
import platform
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text
from sigma_m3.core.db import database
from sigma_m3.core.settings import Settings
from sigma_m3.services.forecast import clean_json
from sigma_m3.core.hashes import digest
from sigma_m3.core.run_context import required_run, source_data_id
from M3.research import daily_validation as base

PROTOCOL = {
    **base.PROTOCOL,
    "id": "daily-panel-validation-v2",
    "candidates": ["lgbm_panel_poisson", "lgbm_panel_mape", "lgbm_route_mape"],
    "objectives": {"lgbm_panel_poisson": "poisson"},
    "route_specific": ["lgbm_route_mape"],
    "categorical_features": ["route_id", "target_weekday", "target_month"],
    "lgbm": {
        **base.PROTOCOL["lgbm"],
        "n_estimators": 350,
        "learning_rate": 0.04,
        "min_child_samples": 60,
    },
}
EXTRA = [
    "count_lag1",
    "count_mean7",
    "count_mean28",
    "count_mean90",
    "units_per_order7",
    "units_per_order28",
    "zero_share90",
    "country_mean7",
    "country_mean28",
    "country_lag1",
    "market_mean7",
    "market_mean28",
    "market_lag1",
    "weekday_mean56",
    "weekday_mean182",
    "weekday_mean365",
    "annual364",
    "annual365",
    "annual366",
    "doy_sin",
    "doy_cos",
]
FEATURES = base.FEATURES + EXTRA


def enrich(daily, top):
    """Aggregate panels are prefix features, never future market observations."""
    daily = daily.sort_values(base.ROUTE + ["date"]).reset_index(drop=True)
    for _, group in daily.groupby(base.ROUTE):
        if (
            not pd.DatetimeIndex(group.date).equals(
                pd.date_range("2024-01-01", PROTOCOL["validation_end"])
            )
            or not group.actual_available.eq(True).all()
            or not np.isfinite(group[["sales_qty", "order_count"]]).all().all()
            or (group[["sales_qty", "order_count"]] < 0).any().any()
            or ((group.order_count == 0) != (group.sales_qty == 0)).any()
        ):
            raise ValueError(
                "Market/count features require a complete observed calendar"
            )
    groups = {key: part.set_index("date") for key, part in daily.groupby(base.ROUTE)}
    market = daily.groupby("date").sales_qty.sum()
    countries = {
        key: part.groupby("date").sales_qty.sum()
        for key, part in daily.groupby("destination_country")
    }
    selected = daily.loc[
        [tuple(k) in top for k in daily[base.ROUTE].itertuples(index=False, name=None)]
    ]
    frame = base.examples(selected)
    origin_features = []
    weekday_maps = {}
    for key in sorted(top):
        part = groups[key]
        values, counts = part.sales_qty, part.order_count
        country = countries[key[0]]
        for origin in frame.as_of_date.unique():
            origin = pd.Timestamp(origin)
            qty = values.loc[:origin]
            orders = counts.loc[:origin]
            c = country.loc[:origin]
            m = market.loc[:origin]
            row = {
                "destination_country": key[0],
                "carrier": key[1],
                "as_of_date": origin,
                "count_lag1": float(orders.iloc[-1]),
                "zero_share90": float(qty.tail(90).eq(0).mean()),
                "country_lag1": float(c.iloc[-1]),
                "market_lag1": float(m.iloc[-1]),
            }
            for days in (7, 28, 90):
                row[f"count_mean{days}"] = float(orders.tail(days).mean())
            for days in (7, 28):
                denominator = orders.tail(days).sum()
                row[f"units_per_order{days}"] = (
                    float(qty.tail(days).sum() / denominator) if denominator else 0.0
                )
                row[f"country_mean{days}"] = float(c.tail(days).mean())
                row[f"market_mean{days}"] = float(m.tail(days).mean())
            for days in (56, 182, 365):
                window = qty.tail(days)
                weekday_maps[(key, origin, days)] = (
                    window.groupby(window.index.dayofweek).mean().to_dict()
                )
            origin_features.append(row)
    frame = frame.merge(
        pd.DataFrame(origin_features),
        on=base.ROUTE + ["as_of_date"],
        validate="many_to_one",
        sort=False,
    )
    for days in (56, 182, 365):
        frame[f"weekday_mean{days}"] = [
            weekday_maps[((r.destination_country, r.carrier), r.as_of_date, days)][
                r.target_weekday
            ]
            for r in frame.itertuples()
        ]
    for days in (364, 365, 366):
        frame[f"annual{days}"] = [
            groups[(r.destination_country, r.carrier)].sales_qty.get(
                r.target_date - pd.Timedelta(days=days), np.nan
            )
            for r in frame.itertuples()
        ]
        # All references are at least350days before origin. Missing early years stay NaN.
        assert (frame.target_date - pd.Timedelta(days=days) <= frame.as_of_date).all()
    frame["doy_sin"] = np.sin(2 * np.pi * frame.target_date.dt.dayofyear / 365.25)
    frame["doy_cos"] = np.cos(2 * np.pi * frame.target_date.dt.dayofyear / 365.25)
    return frame


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
        features=FEATURES,
        created_at=datetime.now(timezone.utc).isoformat(),
        code_hashes={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), Path(base.__file__)]
        },
        requirements_hashes={
            p: hashlib.sha256((root / p).read_bytes()).hexdigest()
            for p in ["requirements.txt", "web/backend/requirements.txt"]
        },
        runtime=dict(
            python=platform.python_version(),
            packages={
                n: version(n) for n in ["lightgbm", "pandas", "numpy", "scikit-learn"]
            },
        ),
        evaluation_limit="Validation used for research; no independent holdout, test read or serving replacement.",
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
                       sum(d.sales_qty) AS sales_qty,sum(d.order_count) AS order_count,
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
        daily = daily.sort_values(base.ROUTE + ["date"]).reset_index(drop=True)
        ranking = (
            daily.loc[daily.date.le(PROTOCOL["train_end"])]
            .groupby(base.ROUTE)
            .sales_qty.sum()
            .sort_values(ascending=False, kind="stable")
        )
        top = set(ranking.head(10).index)
        registered = json.loads((root / "data/configs/m2-final.json").read_text())
        assert top == {
            (r["destination_country"], r["carrier"]) for r in registered["routes"]
        }
        manifest.update(
            status="running",
            observed_rows=len(daily),
            observed_end=daily.date.max().date().isoformat(),
            observed_data_sha256=hashlib.sha256(
                pd.util.hash_pandas_object(daily, index=False).values.tobytes()
            ).hexdigest(),
        )
        save()
        forecasts, metrics, selected, logs = base.evaluate_frame(
            enrich(daily, top), FEATURES, PROTOCOL
        )
        assert len(selected) == 10 and metrics.coverage.eq(1).all()
        assert all(r["max_label_end"] <= r["fit_cutoff"] for r in logs)
        for name, frame in [
            ("validation_predictions", forecasts),
            ("validation_metrics", metrics),
            ("validation_selection", selected),
        ]:
            frame.to_csv(output / (name + ".csv"), index=False)
        (output / "fit_log.json").write_text(
            json.dumps(logs, indent=2), encoding="utf-8"
        )
        manifest.update(
            status="complete",
            routes=10,
            candidates=3,
            prediction_pairs=len(forecasts),
            fits=len(logs),
            selected_mean_mape=float(selected.mape_positive_pct.mean()),
            routes_at_most20=int(selected.mape_positive_pct.le(20).sum()),
            selection_sha256=digest(clean_json(selected.to_dict("records"))),
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
                            "selected_mean_mape",
                            "routes_at_most20",
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
