"""Allowlisted RPC dispatcher for Streamlit React. No filesystem or network paths."""

from copy import deepcopy
import csv
import io
import json
from urllib.parse import urlsplit, parse_qs
from .bundle import clean
from .state import PublicError, initial_state, change_config, create_projection
from .views import (
    run_for,
    context,
    paginate,
    filter_rows,
    dataset,
    operational,
    monthly,
)
from .forecast import forecasts, metrics


def csv_text(rows, metadata):
    fields = sorted(set(metadata) | {key for row in rows for key in row})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        values = clean({**metadata, **row})
        for key, value in values.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str) and value.startswith(
                ("=", "+", "-", "@", "\t", "\r")
            ):
                value = "'" + value
            values[key] = value
        writer.writerow(values)
    return output.getvalue()


class PublicWorkspace:
    def __init__(self, bundle, state=None):
        self.bundle = bundle
        self.state = state if state is not None else initial_state(bundle)

    def call(self, path, method="GET", body=None, idempotency=None):
        try:
            return clean(self.dispatch(path, method, body, idempotency))
        except PublicError as error:
            return dict(
                ok=False,
                status=error.status,
                error=dict(code=error.code, message=str(error)),
            )
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            return dict(
                ok=False,
                status=400,
                error=dict(
                    code="invalid_input",
                    message="Tham số hoặc mốc dữ liệu không hợp lệ. "
                    + str(error)[:180],
                ),
            )

    def dispatch(self, url, method, body, idempotency):
        if not isinstance(url, str) or len(url) > 2048 or ".." in url:
            raise PublicError("Đường dẫn không hợp lệ.")
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            raise PublicError("Chỉ hỗ trợ thao tác nội bộ.")
        raw = parse_qs(parsed.query, keep_blank_values=False)
        if any(len(value) != 1 for value in raw.values()):
            raise PublicError("Tham số trùng.")
        q = {key: value[0] for key, value in raw.items()}
        path = parsed.path
        if method not in ["GET", "POST", "PATCH"]:
            raise PublicError("Phương thức không được hỗ trợ.")
        b, s = self.bundle, self.state
        if method != "GET":
            if len(json.dumps(body)) > 150000:
                raise PublicError("Nội dung cấu hình quá lớn.")
            if path == "/runs" and method == "POST":
                if not isinstance(idempotency, str) or not 8 <= len(idempotency) <= 128:
                    raise PublicError("Thiếu khóa chống gửi lặp.")
                fingerprint = json.dumps(body, sort_keys=True, allow_nan=False)
                prior = s["idempotency"].get(idempotency)
                if prior:
                    if prior["body"] != fingerprint:
                        raise PublicError(
                            "Khóa gửi lặp đã dùng cho nội dung khác.",
                            "version_conflict",
                            409,
                        )
                    return dict(
                        ok=True, status=200, data={**prior["reply"], "reused": True}
                    )
                result = create_projection(b, s, body, idempotency)
                s["idempotency"][idempotency] = dict(body=fingerprint, reply=result)
            else:
                result = change_config(b, s, path, method, body)
            return dict(ok=True, status=200, data=result)
        if path in [
            "/warehouses",
            "/items",
            "/suppliers",
            "/supplier-item-policies",
            "/scenarios",
        ]:
            selected_run = run_for(b, s, q["run_id"]) if q.get("run_id") else None
            if path == "/warehouses":
                rows = (
                    deepcopy(s["warehouses"])
                    if not q.get("run_id")
                    else deepcopy(
                        s["plans"].get(q["run_id"], {}).get("warehouses", b.warehouses)
                    )
                )
            elif path == "/items":
                rows = filter_rows(deepcopy(b.catalog_rows), q)
                if selected_run:
                    rows = [
                        row
                        for row in rows
                        if row["first_seen_date"] <= selected_run["as_of_date"]
                    ]
            elif path == "/suppliers":
                rows = deepcopy(b.suppliers)
            elif path == "/scenarios":
                rows = deepcopy(s["scenarios"])
            else:
                rows = deepcopy(s["policies"])
                for row in rows:
                    info = next(
                        c for c in b.catalog_rows if c["item_id"] == row["item_id"]
                    )
                    row["item_label"] = (
                        f"{info['carrier']} · {info['sku']} · {info['product_type']}"
                    )
            return dict(ok=True, status=200, data=paginate(rows, q))
        if path == "/runs":
            return dict(ok=True, status=200, data=paginate(s["runs"] + b.runs, q))
        parts = path.strip("/").split("/")
        if len(parts) < 2 or parts[0] != "runs":
            raise PublicError("Không tìm thấy chức năng.", "not_found", 404)
        run = run_for(b, s, parts[1])
        tail = "/".join(parts[2:])
        if not tail:
            return dict(ok=True, status=200, data=deepcopy(run))
        ctx = context(b, run)
        export = False
        if tail.startswith("exports/"):
            export = True
            tail = tail.split("/", 1)[1]
            tail = {
                "inventory_daily": "inventory",
                "item_forecasts": "forecasts/items",
                "route_forecasts": "forecasts/routes",
                "monthly_forecasts": "monthly-forecasts",
                "monthly_metrics": "monthly-metrics",
                "replenishments": "replenishments",
            }.get(tail, tail)
        if tail == "purchasing/export":
            tail = "purchasing"
            export = True
        if tail == "workspace":
            return dict(ok=True, status=200, data=operational(b, s, run, q))
        if tail == "purchasing":
            result = operational(b, s, run, q, True)
            rows = result["items"]
            ctx = result["context"]
            if export:
                return dict(
                    ok=True,
                    status=200,
                    csv=csv_text(rows, {**ctx, "run_status": run["status"]}),
                )
            return dict(
                ok=True,
                status=200,
                data={**paginate(rows, q, ctx), "summary": result["summary"]},
            )
        if tail == "alert-opportunities":
            return dict(
                ok=True, status=200, data={"diagnostic": b.meta["alert_opportunities"]}
            )
        if tail.startswith("monthly-"):
            result = monthly(b, run, tail, q)
            if tail == "monthly-summary":
                return dict(ok=True, status=200, data=result)
            rows = result["items"]
            ctx = result["context"]
        elif tail in ["inventory", "alerts", "replenishments"]:
            rows = dataset(
                b,
                s,
                run,
                {
                    "inventory": "inventory",
                    "alerts": "alerts",
                    "replenishments": "receipts",
                }[tail],
                q,
            )
        elif tail in ["forecasts/routes", "forecasts/items"]:
            rows = forecasts(b, tail.split("/")[1], q)
        elif tail == "metrics":
            rows = metrics(b, q)
        else:
            raise PublicError(
                "Không có thao tác này trong bản trực tuyến.", "not_found", 404
            )
        if export:
            return dict(ok=True, status=200, csv=csv_text(rows, ctx))
        return dict(ok=True, status=200, data=paginate(rows, q, ctx))
