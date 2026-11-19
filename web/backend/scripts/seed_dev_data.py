"""Fill an EMPTY dev/test database with SIMULATED warehouse, catalog, purchase-order and dealer data.

Never run it on a database people use: it refuses unless `--yes` is given and the operational ledger
(ops_warehouses / ops_products) is still empty. Everything is labelled "[Dữ liệu giả lập]" and goes through
the app's own services, so balances, ledger and audit rows stay consistent.

Demand comes from the private order CSV (success orders) shifted by whole weeks so weekdays line up:
the business week being seeded maps onto mid-November of the CSV's last year. Run from the repo root after
migrations and `python -m modules.auth.bootstrap`:

    . .\\web\\backend\\scripts\\load_env.ps1
    .\\.venv-m3\\Scripts\\python.exe web\\backend\\scripts\\seed_dev_data.py --yes

Dealer logins get random passwords, written to outputs/dev_seed/dealer-accounts.private.txt (Git-ignored).
"""
import argparse, math, os, random, secrets, sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

from core.db import database
from core.settings import Settings
from models import User  # registers every table for a standalone session
from modules.auth.schemas import UserCreate
from modules.auth.service import create_user
from modules.catalog.models import Supplier
from modules.configuration.models import Policy
from modules.configuration.schemas import PolicyCreate
from modules.configuration.service import create_policy
from modules.dealers import service as dealers
from modules.dealers.schemas import DealerInput, DealerRequestInput, IssueInput, Rejection, Transition
from modules.operations import service as ops
from modules.operations.models import OperationalProduct, OperationalWarehouse, SupplierSettings
from modules.operations.schemas import (OpsEtaChange, OpsMovementInput, OpsOrderInput, OpsOrderTransition, OpsProductInput,
                                        OpsReceiptInput, OpsSupplierSettingsInput, OpsWarehouseInput)

TAG = "[Dữ liệu giả lập]"
KEY = ["destination_country", "carrier", "sku", "product_type"]
STOCKED_ITEMS = 24
WAREHOUSES = [("KHO-HCM", "Kho Hồ Chí Minh", 0.5), ("KHO-HN", "Kho Hà Nội", 0.3), ("KHO-DN", "Kho Đà Nẵng", 0.2)]
DEALERS = [("DL-SGN", "Đại lý Sài Gòn Travel", ["received", "issued", "submitted"]),
           ("DL-HAN", "Đại lý Hà Nội Roaming", ["approved", "submitted", "rejected"]),
           ("DL-DAD", "Đại lý Đà Nẵng eSIM", ["received", "cancelled", "submitted"])]
# Most useful states first, so a catalog with few suppliers still shows received, open and partial orders.
ORDER_KINDS = ["received", "open", "partial", "late", "draft", "eta_changed", "open", "received", "cancelled", "open"]


def load_orders(csv_path):
    columns = ["order_datetime", "order_status", "quantity", "data_gb", "validity_days", *KEY]
    frame = pd.read_csv(csv_path, usecols=columns)
    frame = frame[frame.order_status == "success"].copy()
    frame["day"] = pd.to_datetime(frame.order_datetime, utc=True).dt.date
    return frame


def seed(sessions, csv_path, today, accounts_path, rng_seed=20261119):
    """Seed one transaction; returns a summary. `today` is the business date (UTC+7) the ledger may post up to."""
    rng = random.Random(rng_seed)
    counter = iter(range(1, 10**7))
    key = lambda name: f"dev-seed-{rng_seed}-{name}-{next(counter)}"
    orders = load_orders(csv_path)
    last_year = max(orders.day).year
    start = today - timedelta(days=3)
    # Whole weeks keep weekdays aligned; `start` lands near 17 November of the CSV's last year.
    shift = timedelta(days=((start - date(last_year, 11, 17)).days // 7) * 7)
    daily = orders.groupby([*KEY, "day"]).quantity.sum()
    catalog = orders.drop_duplicates(KEY).set_index(KEY)[["data_gb", "validity_days"]].sort_index()
    recent = orders[orders.day >= date(last_year, 10, 1)].groupby(KEY).quantity.sum()
    top = list(recent.nlargest(STOCKED_ITEMS).index)

    def demand(item, day):
        return int(daily.get((*item, day - shift), 0))

    def want(item, first, last):
        return sum(demand(item, first + timedelta(days=i)) for i in range((last - first).days + 1))

    accounts = []
    with sessions.begin() as s:
        if s.scalar(select(func.count()).select_from(OperationalWarehouse)) or s.scalar(select(func.count()).select_from(OperationalProduct)):
            raise SystemExit("Sổ kho đã có kho hoặc sản phẩm; script chỉ chạy trên DB thử còn trống. Không có gì được ghi.")
        admin = s.scalar(select(User.id).where(User.role == "admin", User.active).order_by(User.id))
        if admin is None:
            raise SystemExit("Chưa có admin. Chạy `python -m modules.auth.bootstrap` trước.")

        warehouses = [(ops.create_warehouse(s, OpsWarehouseInput(code=code, name=name, country="Việt Nam"), admin)["id"], share)
                      for code, name, share in WAREHOUSES]
        items, suppliers = {}, {}
        for item, (gb, days) in catalog.iterrows():
            country, carrier, sku, ptype = item
            label = "eSIM" if ptype == "eSIM" else "SIM vật lý"
            gb, days = (str(value).removesuffix(".0") for value in (gb, days))
            row = ops.create_product(s, OpsProductInput(name=f"{label} {country} {gb}GB/{days} ngày · {carrier}", sku=sku,
                product_type=ptype, carrier=carrier, destination_country=country), admin)
            items[item] = row["id"]
            suppliers.setdefault(row["supplier_id"], []).append(item)
        # Keep a supplier's configured lead time; give the others a simulated one.
        lead = dict(s.execute(select(SupplierSettings.supplier_id, SupplierSettings.lead_time_days)).all())
        for supplier in s.scalars(select(Supplier.id).where(Supplier.id.in_(suppliers)).order_by(Supplier.id)):
            if supplier not in lead:
                lead[supplier] = rng.randint(3, 10)
                ops.set_supplier_settings(s, supplier, OpsSupplierSettingsInput(lead_time_days=lead[supplier], expected_version=0,
                    reason=f"{TAG} lead time mô phỏng 3–10 ngày"), admin)
        # Purchase policy per product (lot ≈ two weeks of demand, ROP floor ≈ demand over the lead time), unless one exists.
        has_policy = set(s.scalars(select(Policy.item_id).where(Policy.item_id.in_(items.values()))))
        for supplier, members in suppliers.items():
            for item in members:
                if items[item] in has_policy:
                    continue
                per_day = want(item, start - timedelta(days=28), start - timedelta(days=1)) / 28
                create_policy(s, PolicyCreate(item_id=items[item], supplier_id=supplier, effective_from=start,
                    configured_rop_floor=max(1, math.ceil(per_day * lead.get(supplier, 7))), fixed_order_qty=max(5, math.ceil(per_day * 14)),
                    safety_days=Decimal(2), warning_horizon_days=7, expected_version=0))

        # Purchase orders for the stocked suppliers, received into the main warehouse in every lifecycle state.
        main = warehouses[0][0]
        stocked = {}
        for item in top:
            stocked.setdefault(next(sid for sid, members in suppliers.items() if item in members), []).append(item)
        plan = []
        for index, supplier in enumerate(sorted(stocked, key=lambda _: rng.random())):
            kind = ORDER_KINDS[index % len(ORDER_KINDS)]
            days = lead.get(supplier, 7)
            ordered = {"received": start - timedelta(days=days), "partial": start + timedelta(days=1) - timedelta(days=days),
                       "late": today - timedelta(days=days + 3), "draft": today, "cancelled": start + timedelta(days=1)}.get(
                       kind, today - timedelta(days=rng.randint(0, 2)))
            lines = [{"item_id": items[item], "warehouse_id": main, "quantity": max(10, want(item, ordered + timedelta(days=days),
                      ordered + timedelta(days=days + 13)))} for item in stocked[supplier]]
            order, _ = ops.create_order(s, OpsOrderInput(supplier_id=supplier, ordered_on=ordered, note=f"{TAG} {kind}", lines=lines), key("po"), admin)
            if kind != "draft":
                order = ops.transition_order(s, order["id"], OpsOrderTransition(expected_version=order["version"]), admin, "confirm")
            if kind == "cancelled":
                order = ops.transition_order(s, order["id"], OpsOrderTransition(expected_version=order["version"], reason=f"{TAG} NCC hết hàng"), admin, "cancel")
            if kind == "eta_changed":
                order = ops.change_eta(s, order["id"], OpsEtaChange(expected_version=order["version"], eta=order["eta"] + timedelta(days=3),
                    reason=f"{TAG} NCC báo chậm 3 ngày"), admin)
            plan.append((order, kind))

        # Day by day (the ledger refuses back-dated documents): opening count, receipts, then sales issues.
        for offset in range((today - start).days + 1):
            day = start + timedelta(days=offset)
            if day == start:
                for item in top:
                    cover = rng.choice([0.3, 0.6, 1.0, 1.0, 1.4, 1.8])  # some items start short on purpose
                    for warehouse, share in warehouses:
                        ops.stock_movement(s, "adjustment", OpsMovementInput(item_id=items[item], warehouse_id=warehouse,
                            quantity=math.ceil(share * cover * want(item, start, start + timedelta(days=13))),
                            expected_balance_version=ops.stock_position(s, warehouse, items[item])["version"], occurred_on=day,
                            external_ref=f"KK-{day:%Y%m%d}", reason=f"{TAG} kiểm kê tồn đầu kỳ"), key("count"), admin)
            for order, kind in plan:
                if kind not in ("received", "partial") or day != max(start, min(order["eta"], today)):
                    continue
                lines = [{"order_line_id": line["id"], "quantity": line["remaining_qty"] if kind == "received" else max(1, line["remaining_qty"] * 6 // 10)}
                         for line in order["lines"]]
                ops.receive_order(s, order["id"], OpsReceiptInput(expected_version=ops.order_view(s, order["id"])["version"], occurred_on=day,
                    external_ref=f"PGH-{order['id']}-{day:%m%d}", reason=TAG, lines=lines), key("gr"), admin)
            for item in top:
                total = demand(item, day)
                for warehouse, share in warehouses:
                    position = ops.stock_position(s, warehouse, items[item])
                    quantity = min(position["on_hand_qty"], round(share * total))
                    if quantity > 0:
                        ops.stock_movement(s, "issue", OpsMovementInput(item_id=items[item], warehouse_id=warehouse, quantity=quantity,
                            expected_balance_version=position["version"], occurred_on=day, external_ref=f"BAN-{day:%Y%m%d}",
                            reason=f"{TAG} bán lẻ theo CSV"), key("gi"), admin)

        # Dealers with one login each and requests in every status, sized from the next two weeks of demand.
        for code, name, statuses in DEALERS:
            dealer = dealers.create_dealer(s, DealerInput(code=code, name=name, contact=f"{TAG} liên hệ giả"), admin)
            username, password = code.lower().replace("-", "."), secrets.token_urlsafe(12)
            user = create_user(s, UserCreate(username=username, password=password, display_name=name, role="dealer", dealer_id=dealer["id"]))
            accounts.append((username, password, name))
            for status in statuses:
                lines = [{"item_id": items[item], "quantity": max(1, want(item, today + timedelta(days=1), today + timedelta(days=14)) // 10)}
                         for item in rng.sample(top, 3)]
                if status in ("issued", "received"):
                    # These examples must be fulfillable after the simulated retail sales
                    # and earlier dealer issues, without inventing extra stock.
                    available = [(w, [(item, ops.stock_position(s, w, items[item])["on_hand_qty"])
                                      for item in top]) for w, _ in warehouses]
                    available = [(w, [(item, qty) for item, qty in rows if qty > 0]) for w, rows in available]
                    source, rows = max(available, key=lambda pair: (len(pair[1]), sum(qty for _, qty in pair[1])))
                    if not rows:
                        raise SystemExit("Không còn tồn để minh họa xuất đại lý; không có dữ liệu thử nào được ghi.")
                    lines = [{"item_id": items[item], "quantity": min(qty, max(1,
                              want(item, today + timedelta(days=1), today + timedelta(days=14)) // 10))}
                             for item, qty in rng.sample(rows, min(3, len(rows)))]
                request, _ = dealers.create_request(s, dealer["id"], DealerRequestInput(note=f"{TAG} hàng cho 2 tuần tới", lines=lines), key("dr"), user.id)
                version = lambda: Transition(expected_version=request["version"])
                if status == "cancelled":
                    request = dealers.cancel(s, request["id"], version(), dealer["id"], user.id)
                if status == "rejected":
                    request = dealers.reject(s, request["id"], Rejection(expected_version=request["version"], reason=f"{TAG} vượt hạn mức tuần"), admin)
                if status in ("approved", "issued", "received"):
                    request = dealers.approve(s, request["id"], version(), admin)
                if status in ("issued", "received"):
                    request, _ = dealers.issue(s, request["id"], IssueInput(expected_version=request["version"], warehouse_id=source, occurred_on=today), key("dgi"), admin)
                if status == "received":
                    request = dealers.receive(s, request["id"], version(), dealer["id"], user.id)
        summary = {"products": len(items), "stocked_products": len(top), "suppliers": len(suppliers), "orders": len(plan),
                   "documents": s.scalar(select(func.count()).select_from(ops.Document)), "dealers": len(DEALERS)}
    accounts_path.parent.mkdir(parents=True, exist_ok=True)
    accounts_path.write_text(f"Tài khoản đại lý THỬ trên DB dev {TAG}\n" + "".join(f"{u}\t{p}\t{n}\n" for u, p, n in accounts), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Nạp dữ liệu giả lập vào DB dev/test còn trống.")
    parser.add_argument("--yes", action="store_true", help="xác nhận đây là DB thử, được phép ghi")
    parser.add_argument("--csv", type=Path, help="đường dẫn CSV order (mặc định <M3_SOURCE_ROOT>/data/sigma_sim_data_orders.csv)")
    args = parser.parse_args()
    settings = Settings.from_env()
    csv_path = args.csv or Path(os.environ.get("M3_SOURCE_ROOT", ".")) / "data" / "sigma_sim_data_orders.csv"
    if not csv_path.is_file():
        sys.exit(f"Không thấy CSV order tại {csv_path}. Đặt bản CSV của nhóm vào đó hoặc truyền --csv.")
    if not args.yes:
        sys.exit("Script ghi dữ liệu giả lập vào DB trong M3_DATABASE_URL. Chỉ dùng cho DB thử; chạy lại kèm --yes để xác nhận.")
    root = Path(__file__).resolve().parents[3]
    engine, sessions = database(settings.database_url)
    try:
        summary = seed(sessions, csv_path, ops.today(), root / "outputs" / "dev_seed" / "dealer-accounts.private.txt")
    finally:
        engine.dispose()
    print(summary)
    print("Tài khoản đại lý thử: outputs/dev_seed/dealer-accounts.private.txt")


if __name__ == "__main__":
    main()
