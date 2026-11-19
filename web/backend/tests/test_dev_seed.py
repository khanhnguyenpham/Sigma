"""Dev seed on real PostgreSQL with a synthetic order CSV; checks the ledger stays consistent and reruns are refused."""
from datetime import date, datetime, time, timedelta, timezone
import csv
import pytest
from sqlalchemy import func, select
from modules.configuration.models import Policy
from modules.dealers.models import DealerRequest
from modules.operations.models import OperationalOrder, OperationalProduct, StockBalance, StockDocumentLine
from test_auth import auth_app  # noqa: F401
from web.backend.scripts.seed_dev_data import seed

TODAY = date(2026, 11, 19)
ROUTES = [("Japan", "CarrierA"), ("Japan", "CarrierB"), ("Korea", "CarrierC")]
BROAD_ROUTES = [("Japan", "SoftBank"), ("Japan", "KDDI"), ("Korea", "SK Telecom"),
                ("Korea", "KT"), ("Thailand", "AIS"), ("Thailand", "TrueMove"),
                ("Singapore", "Singtel"), ("Malaysia", "Maxis"), ("Taiwan", "Chunghwa"), ("China", "China Mobile")]


def write_orders(path, routes=ROUTES, variants=(("D5G-7D", "eSIM"), ("D1G-3D", "physical_SIM"))):
    with path.open("w", newline="", encoding="utf-8") as handle:
        out = csv.writer(handle)
        out.writerow(["order_datetime", "order_status", "quantity", "data_gb", "validity_days", "destination_country", "carrier", "sku", "product_type"])
        day = date(2025, 9, 1)
        while day <= date(2025, 12, 31):
            for n, (country, carrier) in enumerate(routes):
                for sku, ptype in variants:
                    stamp = datetime.combine(day, time(9), timezone.utc).isoformat()
                    out.writerow([stamp, "success", 2 + (n % 4 if len(routes) > 3 else n) + day.weekday() % 3,
                                  5, 7, country, carrier, sku, ptype])
            out.writerow([datetime.combine(day, time(10), timezone.utc).isoformat(), "failed", 50, 5, 7, "Japan", "CarrierA", "D5G-7D", "eSIM"])
            day += timedelta(days=1)


@pytest.mark.parametrize("today,routes,variants", [
    (TODAY, ROUTES, (("D5G-7D", "eSIM"), ("D1G-3D", "physical_SIM"))),
    (date(2026, 11, 20), BROAD_ROUTES,
     [(sku, kind) for sku in ("D1G-3D", "D5G-7D") for kind in ("eSIM", "physical_SIM")]),
])
def test_seed_fills_an_empty_ledger_consistently_and_refuses_a_second_run(auth_app, tmp_path, today, routes, variants):
    _, sessions = auth_app
    orders = tmp_path / "orders.csv"; write_orders(orders, routes, variants)
    accounts = tmp_path / "accounts.txt"
    summary = seed(sessions, orders, today, accounts)
    expected_products = len(routes) * len(variants)
    assert summary["products"] == expected_products and summary["dealers"] == 3
    with sessions() as s:
        assert s.scalar(select(func.count()).select_from(OperationalProduct)) == expected_products
        assert s.scalar(select(func.count()).select_from(Policy).where(Policy.item_id.in_(select(OperationalProduct.item_id)))) == expected_products
        # Every balance equals the sum of its ledger lines, and none went negative.
        ledger = dict(((w, i), q) for w, i, q in s.execute(select(StockDocumentLine.warehouse_id, StockDocumentLine.item_id,
            func.sum(StockDocumentLine.quantity_delta)).group_by(StockDocumentLine.warehouse_id, StockDocumentLine.item_id)))
        balances = {(b.warehouse_id, b.item_id): b.on_hand_qty for b in s.scalars(select(StockBalance))}
        assert balances == ledger and min(balances.values()) >= 0
        assert s.scalar(select(func.max(StockBalance.last_movement_on))) <= today
        expected_statuses = {"received", "ordered", "partially_received"}
        if summary["orders"] >= 5:
            expected_statuses.add("draft")
        if summary["orders"] >= 9:
            expected_statuses.add("cancelled")
        assert set(s.scalars(select(OperationalOrder.status))) == expected_statuses
        assert set(s.scalars(select(DealerRequest.status).where(DealerRequest.request_key.like("dev-seed-%")))) == {
            "submitted", "approved", "issued", "received", "rejected", "cancelled"}
    assert len(accounts.read_text(encoding="utf-8").splitlines()) == 4
    with pytest.raises(SystemExit, match="DB thử còn trống"):
        seed(sessions, orders, today, accounts)
