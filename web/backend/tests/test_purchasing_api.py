"""Purchasing views share frozen scope, searches and as-of receipt state with CSV."""

import csv
import io
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from main import create_app
from modules.runs.models import Run
from modules.purchasing.models import Replenishment
from test_postgres_api import settings, D
from test_workspace_api import workspace_fixture


def test_purchasing_views_do_not_use_future_orders_or_final_receipt_status(
    pg, tmp_path
):
    _, sessions = pg
    key, _, _ = workspace_fixture(sessions)
    root = f"/api/v1/runs/{key}/purchasing"
    with TestClient(create_app(settings(tmp_path))) as client:
        query = f"as_of_date={D}&search=demoland%20esim"
        incoming = client.get(root + "?" + query + "&view=incoming").json()
        assert incoming["total"] == 1 and incoming["summary"]["pending_units"] == 20
        assert (
            incoming["items"][0]["status"] == "ordered"
            and incoming["items"][0]["received_qty"] == 0
        )
        assert (
            incoming["summary"]["historical_lots"] == 2
            and incoming["summary"]["recommended_items"] == 0
        )
        history = client.get(
            root + "?" + query + "&view=history&sort=ordered_desc&page_size=1"
        ).json()
        assert history["total"] == 2 and len(history["items"]) == 1
        assert history["items"][0]["order_key"] == "known"
        exported = client.get(
            root
            + "/export?"
            + query
            + "&view=history&sort=ordered_desc&page_size=1&page=2"
        )
        assert exported.status_code == 200
        rows = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
        assert len(rows) == 2 and {r["order_key"] for r in rows} == {"past", "known"}
        assert rows[0]["received_qty"] == "0" and rows[0]["run_status"] == "complete"
        assert (
            rows[0]["view_date"] == D.isoformat()
            and rows[0]["search"] == "demoland esim"
        )
        later = client.get(
            root + f"?as_of_date={D + timedelta(days=4)}&view=history"
        ).json()
        assert later["total"] == 3
        assert (
            next(row for row in later["items"] if row["order_key"] == "known")["status"]
            == "received"
        )
        assert (
            next(row for row in later["items"] if row["order_key"] == "future")[
                "status"
            ]
            == "ordered"
        )
        absent = client.get(
            root + f"?as_of_date={D}&view=incoming&search=does-not-exist"
        ).json()
        assert absent["total"] == 0 and absent["summary"]["incoming_lots"] == 0
        assert (
            client.get(root + f"?as_of_date={D}&view=incoming&search=%25").json()[
                "total"
            ]
            == 0
        )
    with sessions() as session:
        assert (
            session.scalar(
                select(Replenishment).where(
                    Replenishment.run_id == key, Replenishment.order_key == "known"
                )
            ).received_qty
            == 20
        )


def test_purchasing_recommendations_and_snapshot_bounds(pg, tmp_path):
    _, sessions = pg
    key, parent, item = workspace_fixture(sessions, pending=False)
    root = f"/api/v1/runs/{key}/purchasing"
    with TestClient(create_app(settings(tmp_path))) as client:
        data = client.get(
            root + f"?as_of_date={D}&search=demo-esim&sort=quantity_asc"
        ).json()
        assert data["total"] == 1 and data["summary"]["recommended_units"] == 14
        assert data["items"][0]["item_id"] == item
        assert (
            client.get(root + f"?as_of_date={D}&product_type=physical_SIM").json()[
                "total"
            ]
            == 0
        )
        assert client.get(root + f"?as_of_date={D}&sort=bad").status_code == 422
        assert (
            client.get(root + f"?as_of_date={D}&search=" + "x" * 81).status_code == 422
        )
        assert client.get(root + f"?as_of_date={D}&view=bad").status_code == 422
        assert (
            client.get(f"/api/v1/runs/{parent}/purchasing?as_of_date={D}").status_code
            == 409
        )
        with sessions.begin() as session:
            session.get(Run, key).kind = "stock_projection"
        snap = client.get(
            root + f"?as_of_date={D + timedelta(days=15)}&view=history"
        ).json()
        assert snap["context"]["known_orders_through"] == D.isoformat()
        assert snap["total"] == 2 and not snap["summary"]["inventory_available"]
        with sessions.begin() as session:
            session.get(Run, key).status = "running"
        assert client.get(root + f"?as_of_date={D}").status_code == 409
