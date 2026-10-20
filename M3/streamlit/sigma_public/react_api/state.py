"""Isolated public configuration and forward projections; no database or training."""

from copy import deepcopy
from datetime import date, timedelta, datetime, timezone
import math
import re
import uuid
from sigma_m3.services.inventory import PolicyValues, recommend
from sigma_m3.services.alerts import project
from .bundle import records


class PublicError(ValueError):
    def __init__(self, message, code="invalid_input", status=400):
        super().__init__(message)
        self.code = code
        self.status = status


def day(value):
    try:
        parsed = date.fromisoformat(str(value))
        if str(parsed) != value:
            raise ValueError()
        return parsed
    except (TypeError, ValueError):
        raise PublicError("Ngày phải theo dạng YYYY-MM-DD.")


def integer(value, minimum=0, maximum=1000000):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise PublicError("Giá trị phải là số nguyên.")
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise PublicError("Giá trị phải là số nguyên.")
    if (
        not minimum <= result <= maximum
        or isinstance(value, str)
        and str(result) != value
    ):
        raise PublicError("Số nguyên vượt phạm vi cho phép.")
    return result


def finite(value, minimum=0, maximum=100):
    if isinstance(value, bool):
        raise PublicError("Tham số số không hợp lệ.")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise PublicError("Tham số số không hợp lệ.")
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise PublicError("Tham số vượt phạm vi cho phép.")
    return result


def initial_state(bundle):
    policies = [
        dict(
            id=row["item_id"],
            item_id=row["item_id"],
            supplier_id=row["supplier_id"],
            supplier_code=row["supplier"],
            version=1,
            effective_from="2024-01-01",
            effective_to=None,
            configured_rop_floor=row["configured_rop_floor"],
            moq=row["moq"],
            safety_days=row["safety_days"],
            is_assumed=True,
            assumption_source="public aggregate defaults; effective date is an online assumption",
        )
        for row in bundle.catalog_rows
    ]
    return dict(
        warehouses=deepcopy(bundle.warehouses),
        policies=policies,
        scenarios=[
            dict(
                id=1,
                code="base_public",
                name="Cơ sở trực tuyến",
                version=1,
                description="Số tồn từ snapshot công khai; lô đầu kỳ được khai báo trong kịch bản.",
                settings=dict(
                    cover_days=7,
                    safety_multiplier=1,
                    policy_overrides=[],
                    receipts_initial=[],
                    receipts_declared=True,
                    inventory_seed_mode="published_closing",
                ),
            )
        ],
        runs=[],
        plans={},
        idempotency={},
    )


def policy_for(policies, item, origin):
    choices = [
        p
        for p in policies
        if p["item_id"] == item
        and p["effective_from"] <= origin
        and (p["effective_to"] is None or p["effective_to"] > origin)
    ]
    if len(choices) != 1:
        raise PublicError(
            "Chưa có chính sách hiệu lực cho mặt hàng tại mốc chọn.",
            "missing_partner_config",
        )
    return choices[0]


def change_config(bundle, state, path, method, body):
    if not isinstance(body, dict):
        raise PublicError("Nội dung cấu hình phải là đối tượng JSON.")
    if path.startswith("/warehouses/") and method == "PATCH":
        ident = integer(path.rsplit("/", 1)[1], 1, len(bundle.warehouses))
        row = next(w for w in state["warehouses"] if w["id"] == ident)
        if body.get("expected_version") != row["version"]:
            raise PublicError("Cấu hình đã thay đổi.", "version_conflict", 409)
        city = body.get("city")
        if not isinstance(city, str) or not 1 <= len(city.strip()) <= 120:
            raise PublicError("Thành phố cần 1–120 ký tự.")
        row.update(city=city.strip(), version=row["version"] + 1)
        return deepcopy(row)
    if path == "/supplier-item-policies" and method == "POST":
        if len(state["policies"]) >= 2048:
            raise PublicError("Phiên này đã có đủ phiên bản chính sách.")
        item = integer(body.get("item_id"), 1, 920)
        supplier = integer(body.get("supplier_id"), 1, 46)
        effective = str(day(body.get("effective_from")))
        old = [p for p in state["policies"] if p["item_id"] == item]
        latest = max(old, key=lambda p: p["version"])
        if body.get("expected_version") != latest["version"]:
            raise PublicError("Phiên bản đã thay đổi.", "version_conflict", 409)
        if effective <= latest["effective_from"]:
            raise PublicError(
                "Ngày hiệu lực mới phải sau bản đang có; dùng điều chỉnh riêng trong kịch bản để thử lịch sử.",
                "version_conflict",
                409,
            )
        values = dict(
            configured_rop_floor=integer(body.get("configured_rop_floor")),
            moq=integer(body.get("moq"), 1),
            safety_days=finite(body.get("safety_days")),
        )
        latest["effective_to"] = effective
        row = dict(
            **{
                k: v
                for k, v in latest.items()
                if k not in values
                and k
                not in {
                    "id",
                    "supplier_id",
                    "supplier_code",
                    "version",
                    "effective_from",
                    "effective_to",
                }
            },
            **values,
            id=max(p["id"] for p in state["policies"]) + 1,
            supplier_id=supplier,
            supplier_code=f"SUP-{supplier:03d}",
            version=latest["version"] + 1,
            effective_from=effective,
            effective_to=None,
        )
        state["policies"].append(row)
        return deepcopy(row)
    if path == "/scenarios" and method == "POST":
        if len(state["scenarios"]) >= 40:
            raise PublicError("Phiên này đã có đủ 40 kịch bản.")
        name, code, description = (
            body.get("name"),
            body.get("code"),
            body.get("description", ""),
        )
        if (
            not isinstance(name, str)
            or not 1 <= len(name.strip()) <= 120
            or not isinstance(code, str)
            or not re.fullmatch("[a-z0-9_-]{1,64}", code)
        ):
            raise PublicError("Tên hoặc mã kịch bản không hợp lệ.")
        if not isinstance(description, str) or len(description) > 1000:
            raise PublicError("Ghi chú quá dài.")
        config = deepcopy(body.get("settings"))
        if not isinstance(config, dict) or config.get("receipts_declared") is not True:
            raise PublicError("Cần khai báo rõ danh sách lô đầu kỳ.")
        if config.get("cover_days") != 7:
            raise PublicError(
                "Bản trực tuyến lấy số tồn đã công bố, không tái dựng lịch sử bằng số ngày phủ."
            )
        config["safety_multiplier"] = finite(config.get("safety_multiplier"), 0, 10)
        overrides = config.get("policy_overrides", [])
        receipts = config.get("receipts_initial", [])
        if (
            not isinstance(overrides, list)
            or not isinstance(receipts, list)
            or max(len(overrides), len(receipts)) > 100
        ):
            raise PublicError("Tối đa 100 điều chỉnh/lô mỗi kịch bản.")
        seen = set()
        for row in overrides:
            if not isinstance(row, dict):
                raise PublicError("Điều chỉnh phải là đối tượng JSON.")
            item = integer(row.get("item_id"), 1, 920)
            if item in seen:
                raise PublicError("Điều chỉnh mặt hàng bị trùng.")
            seen.add(item)
            integer(row.get("configured_rop_floor"))
            integer(row.get("moq"), 1)
            finite(row.get("safety_days"))
        seen = set()
        for row in receipts:
            if not isinstance(row, dict):
                raise PublicError("Lô hàng phải là đối tượng JSON.")
            integer(row.get("item_id"), 1, 920)
            integer(row.get("quantity"), 1)
            ordered, arrival = day(row.get("ordered_on")), day(row.get("eta"))
            if arrival != ordered + timedelta(days=7):
                raise PublicError("ETA phải đúng ngày đặt +7.")
            key = row.get("receipt_key") or row.get("key") or row.get("lot_key")
            if not isinstance(key, str) or not 1 <= len(key) <= 64 or key in seen:
                raise PublicError("Mã lô thiếu, trùng hoặc quá dài.")
            seen.add(key)
        config["inventory_seed_mode"] = "published_closing"
        row = dict(
            id=max(s["id"] for s in state["scenarios"]) + 1,
            code=code,
            name=name.strip(),
            description=description,
            version=1
            + max(
                [s["version"] for s in state["scenarios"] if s["code"] == code],
                default=0,
            ),
            settings=config,
        )
        state["scenarios"].append(row)
        return deepcopy(row)
    raise PublicError(
        "Thao tác không được hỗ trợ trên phiên trực tuyến.", "not_found", 404
    )


def create_projection(bundle, state, body, request_key):
    if not isinstance(body, dict) or body.get("kind") != "stock_projection":
        raise PublicError(
            "Trực tuyến chỉ tạo dự phóng tồn; huấn luyện và replay giao dịch chạy local."
        )
    if len(state["runs"]) >= 8:
        raise PublicError("Phiên này đã có đủ 8 phương án.")
    if (
        body.get("forecast_run_id") != bundle.forecast_id
        or body.get("source_import_run_id") != "public-source"
    ):
        raise PublicError("Nguồn/dự báo không tương thích.", "parent_mismatch", 409)
    origin = str(day(body.get("as_of_date")))
    if origin not in bundle.origin_index:
        raise PublicError(
            "Mốc chọn không có forecast14 đủ nhãn.", "insufficient_forecast"
        )
    scenario = next(
        (s for s in state["scenarios"] if s["id"] == body.get("scenario_id")), None
    )
    if not scenario:
        raise PublicError("Không tìm thấy kịch bản.", "not_found", 404)
    settings = deepcopy(scenario["settings"])
    seed = bundle.seed_inventory(origin)
    overrides = {r["item_id"]: r for r in settings["policy_overrides"]}
    receipts = []
    for j, row in enumerate(settings["receipts_initial"]):
        ordered, arrival = day(row["ordered_on"]), day(row["eta"])
        if not ordered <= day(origin) < arrival:
            raise PublicError("Lô đầu kỳ phải đã đặt và chưa đến ETA tại mốc chọn.")
        item = integer(row["item_id"], 1, 920)
        receipts.append(
            dict(
                id=100000 + j,
                item_id=item,
                ordered_on=str(ordered),
                eta=str(arrival),
                ordered_qty=integer(row["quantity"], 1),
                received_qty=0,
                status="ordered",
                is_initial=True,
                is_simulated=True,
            )
        )
    rows = []
    alerts = []
    policies = deepcopy(state["policies"])
    for old in records(seed):
        item = old["item_id"]
        info = next(c for c in bundle.catalog_rows if c["item_id"] == item)
        policy = deepcopy(policy_for(policies, item, origin))
        policy.update(
            {
                k: v
                for k, v in overrides.get(item, {}).items()
                if k in {"configured_rop_floor", "moq", "safety_days"}
            }
        )
        policy["safety_days"] *= settings["safety_multiplier"]
        vector = bundle.vector(origin, item)
        lots = [r for r in receipts if r["item_id"] == item]
        pending = sum(r["ordered_qty"] for r in lots)
        stock = int(old["closing_qty"])
        decision = recommend(
            vector,
            stock,
            pending,
            PolicyValues(
                policy["configured_rop_floor"], policy["moq"], policy["safety_days"]
            ),
        )
        row = {
            **info,
            **decision,
            "id": item,
            "date": origin,
            "opening_qty": stock,
            "closing_qty": stock,
            "receipts_qty": 0,
            "sales_qty": 0,
            "fulfilled_qty": 0,
            "shortage_qty": 0,
            "config_status": "complete",
            "configured_rop_floor": policy["configured_rop_floor"],
            "moq": policy["moq"],
            "safety_days": policy["safety_days"],
            "policy_version": policy["version"],
            "supplier_id": policy["supplier_id"],
            "is_simulated": True,
            "eta_if_ordered": str(day(origin) + timedelta(days=7))
            if decision["recommended_qty"]
            else None,
        }
        rows.append(row)
        known = {}
        for lot in lots:
            known[day(lot["eta"])] = known.get(day(lot["eta"]), 0) + lot["ordered_qty"]
        projected = project(day(origin), stock, vector, known)
        base = {
            **info,
            "id": item * 2,
            "as_of_date": origin,
            "is_simulated": True,
            "actual_depletion_date": None,
            "evaluation_class": None,
            "is_evaluable": False,
            "exclusion_reason": "session_projection_no_future_actual",
        }
        alerts.append(
            {
                **base,
                **projected,
                "alert_type": "depletion",
                "explanation": {"projection": projected["projection"]},
            }
        )
        if decision["needs_replenishment"]:
            alerts.append(
                {
                    **base,
                    "id": item * 2 + 1,
                    "alert_type": "below_rop",
                    "state": decision["state"],
                    "predicted_depletion_date": None,
                    "lead_days": None,
                    "explanation": {},
                }
            )
        for lot in lots:
            lot.update(
                {
                    k: row[k]
                    for k in [
                        "sku",
                        "carrier",
                        "destination_country",
                        "product_type",
                        "warehouse_id",
                        "supplier_id",
                        "policy_version",
                    ]
                }
            )
    ident = str(uuid.uuid4())
    row = dict(
        id=ident,
        kind="stock_projection",
        status="complete",
        as_of_date=origin,
        observation_end=bundle.meta["observation_end"],
        source_import_run_id="public-source",
        forecast_run_id=bundle.forecast_id,
        scenario_id=scenario["id"],
        config_version=f"public-session-{scenario['version']}",
        assumption_version="published-closing-session-v1",
        target_version=bundle.meta["target_version"],
        error_code=None,
        result_summary={
            "phase": "verified",
            "items": len(rows),
            "inventory_available": True,
            "is_simulated": True,
            "initialization_basis": "published_closing_at_origin",
            "persistence": "current_session_only",
        },
        period_start=None,
        period_end=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    assert len(rows) == 920 and all(
        r["inventory_position"] == r["closing_qty"] + r["pending_qty"] for r in rows
    )
    state["plans"][ident] = dict(
        inventory=rows,
        receipts=receipts,
        alerts=alerts,
        warehouses=deepcopy(state["warehouses"]),
        policies=policies,
    )
    state["runs"].insert(0, row)
    return {"run_id": ident, "status": "complete", "reused": False}
