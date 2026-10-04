"""EDA, public-calendar provenance and synthetic demo data."""
from __future__ import annotations

from pathlib import Path
import os

import holidays
import numpy as np
import pandas as pd

from src.common import ROOT, ROUTE, write_csv, write_json
from src.data import SOURCE_COLUMNS

COUNTRY_CODES = {
    "Vietnam": "VN", "Viet Nam": "VN", "Thailand": "TH", "Singapore": "SG", "Malaysia": "MY",
    "Indonesia": "ID", "Philippines": "PH", "Japan": "JP", "South Korea": "KR", "Korea": "KR",
    "China": "CN", "Taiwan": "TW", "Hong Kong": "HK", "Australia": "AU", "New Zealand": "NZ",
    "United States": "US", "USA": "US", "United Kingdom": "GB", "UK": "GB", "France": "FR",
    "Germany": "DE", "Italy": "IT", "Spain": "ES", "Canada": "CA", "India": "IN", "Turkey": "TR",
    "United Arab Emirates": "AE", "UAE": "AE", "Cambodia": "KH", "Laos": "LA",
}


def calendar_table(countries, cfg):
    days = pd.date_range(cfg["observation_start"], pd.Timestamp(cfg["observation_end"]) + pd.Timedelta(days=cfg["horizon"]))
    records = []
    for country in sorted(countries):
        code = COUNTRY_CODES.get(country)
        calendar = holidays.country_holidays(code, years=sorted(set(days.year))) if code else None
        for day in days:
            records.append({"destination_country": country, "date": day,
                            "country_code": code, "holiday_name": calendar.get(day.date(), "") if calendar is not None else None,
                            "holiday_known": calendar is not None, "weekday": day.dayofweek,
                            "source": "https://github.com/vacanza/holidays", "access_date": "2026-10-05",
                            "limitation": "retrospective public-calendar reference; not used as a future-known anomaly flag"})
    return pd.DataFrame(records)


def eda(daily, folder, cfg):
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    folder = Path(folder)
    figure_dir = folder / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    calendar = calendar_table(daily.destination_country.unique(), cfg)
    write_csv(folder / "calendar.csv", calendar)
    holiday_daily = daily.merge(calendar[["destination_country", "date", "holiday_known", "holiday_name"]],
                                on=["destination_country", "date"], how="left", validate="many_to_one")
    holiday_daily["holiday_group"] = np.where(~holiday_daily.holiday_known.fillna(False), "unknown",
                                             np.where(holiday_daily.holiday_name.fillna("").ne(""), "holiday", "ordinary"))
    holiday_summary = holiday_daily.groupby(["destination_country", "holiday_group"]).sales_qty.agg(
        mean_quantity="mean", total_quantity="sum", labeled_route_days="count").reset_index()
    holiday_summary["interpretation"] = "Descriptive association; unequal samples, weekday/season/product mix can confound; unknown is not ordinary"
    write_csv(folder / "eda_holidays.csv", holiday_summary)
    pooled = holiday_daily.groupby("holiday_group").sales_qty.agg(["mean", "count"])
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(pooled.index, pooled["mean"], color="#7c3aed")
    for index, (_, row) in enumerate(pooled.iterrows()):
        ax.text(index, row["mean"], f"n={int(row['count'])}", ha="center", va="bottom")
    ax.set(xlabel="Public-calendar category; unknown kept separately", ylabel="Mean sales quantity / labeled route-day",
           title="Descriptive holiday association; not a causal effect")
    fig.tight_layout(); fig.savefig(figure_dir / "holidays.png", dpi=150); plt.close(fig)
    route_summary = daily.groupby(ROUTE).agg(total_sales_qty=("sales_qty", "sum"),
                                            observed_days=("sales_qty", "count"),
                                            zero_days=("sales_qty", lambda x: int(x.eq(0).sum())),
                                            mean_daily_qty=("sales_qty", "mean"), std_daily_qty=("sales_qty", "std")).reset_index()
    write_csv(folder / "eda_routes.csv", route_summary)
    weekly = daily.assign(weekday=daily.date.dt.dayofweek).groupby("weekday").sales_qty.agg(["mean", "count"]).reset_index()
    write_csv(folder / "eda_weekday.csv", weekly)
    monthly = daily.assign(month=daily.date.dt.to_period("M").astype(str)).groupby("month").sales_qty.agg(["sum", "mean", "count"]).reset_index()
    write_csv(folder / "eda_monthly.csv", monthly)
    aggregate = daily.groupby("date").sales_qty.sum(min_count=1)
    fig, ax = plt.subplots(figsize=(11, 4))
    aggregate.plot(ax=ax, color="#2563eb", linewidth=1)
    ax.set(xlabel="UTC date", ylabel="Observed sales quantity (units)", title="Sales snapshot — declared status filter, all routes")
    fig.tight_layout(); fig.savefig(figure_dir / "daily_sales.png", dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(weekly.weekday, weekly["mean"], color="#0d9488")
    ax.set(xlabel="UTC weekday (Monday=0)", ylabel="Mean quantity / route-day", title="Descriptive weekly pattern, not a causal claim")
    fig.tight_layout(); fig.savefig(figure_dir / "weekday.png", dpi=150); plt.close(fig)
    write_json(folder / "eda_notes.json", {"filter": cfg["sales_statuses"], "unit": "product quantity",
                                           "scope": [cfg["observation_start"], cfg["observation_end"]],
                                           "missing_is_not_zero": True, "causality_claim": False,
                                           "tourism_season_is_hypothesis": True,
                                           "unknown_calendar_destinations": sorted(set(daily.destination_country) - set(COUNTRY_CODES))})


def generate_synthetic(path, cfg, route_count=3):
    rng = np.random.default_rng(cfg["seed"])
    rows = []
    sequence = 0
    for day in pd.date_range(cfg["observation_start"], cfg["observation_end"]):
        for route in range(route_count):
            count = rng.poisson(8 + route * 3 + (2 if day.dayofweek < 5 else 0))
            for _ in range(count):
                sequence += 1
                qty = int(rng.integers(1, 5))
                row = dict.fromkeys(SOURCE_COLUMNS, "synthetic")
                row.update(order_id=f"SYN-{sequence:08d}", customer_id=f"SYN-C-{sequence:08d}",
                           order_datetime=f"{day.date()}T12:00:00Z", activation_datetime="",
                           destination_country="Vietnam" if route == 0 else f"Synthetic-{route}",
                           carrier="Vinaphone" if route == 0 else f"SyntheticCarrier-{route}",
                           sku=f"SYN-SKU-{route}-{sequence % 2}", product_type="eSIM", plan_type="synthetic",
                           quantity=str(qty), data_gb="5", validity_days="7", unit_price_vnd="1000",
                           unit_cost_vnd="500", gross_revenue_vnd=str(qty * 1000), order_status="success")
                rows.append(row)
    write_csv(path, pd.DataFrame(rows, columns=SOURCE_COLUMNS))
    return Path(path)
