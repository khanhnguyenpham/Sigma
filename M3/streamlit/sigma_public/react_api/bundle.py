"""Public-release adapters. IDs below are release ordinals, never order/customer IDs."""

from datetime import date, timedelta
import json
import math
import pandas as pd
from sigma_public import runtime


def records(frame):
    return json.loads(
        frame.to_json(orient="records", date_format="iso", double_precision=15)
    )


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (date, pd.Timestamp)):
        return str(value)[:10]
    if hasattr(value, "item"):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


class PublicBundle:
    def __init__(self, folder):
        self.meta, self.pin = runtime.manifest(folder)
        self.frames = {
            name: runtime.table(folder, self.meta, name) for name in runtime.TABLES
        }
        self.cube, self.origins = runtime.item_cube(folder, self.meta)
        self.origin_index = {str(day): i for i, day in enumerate(self.origins)}
        catalog = self.frames["catalog"].copy()
        routes = (
            catalog[["destination_country", "carrier"]]
            .drop_duplicates()
            .sort_values(["destination_country", "carrier"])
            .reset_index(drop=True)
        )
        routes["id"] = routes.index + 1
        routes["code"] = [f"WH-{i:03d}" for i in routes.id]
        routes["city"] = ""
        routes["version"] = 1
        routes["is_assumed"] = True
        self.warehouses = records(routes)
        catalog = catalog.merge(
            routes[["destination_country", "carrier", "id"]].rename(
                columns={"id": "warehouse_id"}
            ),
            on=["destination_country", "carrier"],
            validate="many_to_one",
        )
        catalog["id"] = catalog.item_key + 1
        catalog["item_id"] = catalog.id
        catalog["supplier_id"] = catalog.supplier.str.removeprefix("SUP-").astype(int)
        self.catalog = catalog
        self.catalog_rows = records(catalog)
        self.route_ids = {
            (row["destination_country"], row["carrier"]): row["id"]
            for row in self.warehouses
        }
        self.suppliers = [
            dict(id=int(code.split("-")[-1]), code=code, name=code, is_assumed=True)
            for code in sorted(catalog.supplier.unique())
        ]
        self.tables = {}
        joined = ["inventory", "receipts", "alerts"]
        cols = [
            "item_key",
            "warehouse_id",
            "item_id",
            "sku",
            "destination_country",
            "carrier",
            "product_type",
            "configured_rop_floor",
            "moq",
            "safety_days",
            "supplier_id",
        ]
        for name in joined:
            frame = (
                self.frames[name]
                .copy()
                .merge(catalog[cols], on="item_key", validate="many_to_one")
            )
            frame["id"] = frame.index + 1
            frame["is_simulated"] = True
            if name == "inventory":
                # A larger ROP than the forecast uniquely identifies the applied floor.
                frame["configured_rop_floor"] = frame.configured_rop_floor.where(
                    frame.rop <= frame.rop_forecast, frame.rop
                )
                frame["eta_if_ordered"] = [
                    (date.fromisoformat(day) + timedelta(days=7)).isoformat()
                    if q
                    else None
                    for day, q in zip(frame.date, frame.recommended_qty)
                ]
            self.tables[name] = frame
        self.actual = self.tables["inventory"].query("run_label == 'policy_base'")
        self.route_actual = {
            (r.destination_country, r.carrier, r.date): r.sales_qty
            for r in self.frames["route_daily"].itertuples()
        }
        self.item_actual = {
            (int(r.item_id), r.date): r.sales_qty for r in self.actual.itertuples()
        }
        self.forecast_id = self.meta["runs"]["weekly46"]["run_id"]
        self.run_labels = {v["run_id"]: k for k, v in self.meta["runs"].items()}
        self.runs = []
        for label in [
            "snapshot_2025-10-31_pending",
            "snapshot_2025-12-31",
            "policy_base",
            "alert_base",
            "weekly46",
        ]:
            spec = self.meta["runs"][label]
            summary = {
                "phase": "verified",
                "routes": 46,
                "items": 920,
                "inventory_available": label != "alert_base",
                "is_simulated": spec["kind"] != "forecast",
            }
            if label == "weekly46":
                summary["origins"] = len(self.origins)
            if label == "alert_base":
                summary["alert_metrics"] = self.meta["alert_metrics"]
            self.runs.append(
                dict(
                    id=spec["run_id"],
                    kind=spec["kind"],
                    status="complete",
                    as_of_date=spec["origin"],
                    observation_end=self.meta["observation_end"],
                    source_import_run_id="public-source",
                    forecast_run_id=None
                    if spec["kind"] == "forecast"
                    else self.forecast_id,
                    scenario_id=1,
                    config_version=spec["config_sha256"][:12],
                    assumption_version="public-aggregate-v1",
                    target_version=self.meta["target_version"],
                    error_code=None,
                    result_summary=summary,
                    period_start="2025-10-01"
                    if spec["kind"].endswith("replay")
                    else None,
                    period_end="2025-12-31"
                    if spec["kind"].endswith("replay")
                    else None,
                    created_at=self.meta["prepared_at_utc"],
                )
            )

    def vector(self, origin, item_id):
        if origin not in self.origin_index or not 1 <= item_id <= len(self.catalog):
            raise ValueError("Không có đủ dự báo 14 ngày tại mốc đã chọn.")
        return self.cube[self.origin_index[origin], item_id - 1, :].copy()

    def frame(self, name, run_id):
        label = self.run_labels.get(run_id)
        frame = self.tables[name]
        return frame[frame.run_label == label].copy()

    def seed_inventory(self, origin):
        snapshot = "snapshot_" + origin + ("_pending" if origin == "2025-10-31" else "")
        label = snapshot if snapshot in self.meta["runs"] else "policy_base"
        result = self.tables["inventory"]
        result = result[(result.run_label == label) & (result.date == origin)].copy()
        if len(result) != 920:
            raise ValueError(
                "Mốc này chưa có đầy đủ số tồn công khai để tạo phương án. Chọn mốc trong 01/10–31/12/2025."
            )
        return result
