"""Operational dashboard respects frozen scope and as-of knowledge, not final lot status."""

from datetime import timedelta
from fastapi.testclient import TestClient
from sigma_m3.main import create_app
from sigma_m3.models import Run, InventoryDaily, Replenishment, Alert
from sigma_m3.modules.configuration.models import Policy
from sigma_m3.core.hashes import digest
from test_postgres_api import settings, D
from test_results_api import result_fixture


def workspace_fixture(sessions, pending=True):
    _, parent, item = result_fixture(sessions)
    with sessions.begin() as s:
        policy = Policy(
            item_id=item,
            supplier_id=1,
            version=1,
            effective_from=D - timedelta(days=90),
            configured_rop_floor=20,
            moq=10,
            safety_days=2,
            is_assumed=True,
            assumption_source="synthetic",
        )
        s.add(policy)
        s.flush()
        base = s.get(Run, parent)
        attrs = {
            c.name: getattr(base, c.name)
            for c in Run.__table__.columns
            if c.name not in {"id", "created_at"}
        }
        snapshot = {
            **base.config_snapshot,
            "policies": [
                dict(
                    id=policy.id,
                    item_id=item,
                    supplier_id=1,
                    configured_rop_floor=20,
                    moq=10,
                    safety_days=2,
                    version=1,
                )
            ],
        }
        attrs.update(
            kind="policy_replay",
            forecast_run_id=parent,
            as_of_date=D,
            period_start=D,
            period_end=D + timedelta(days=20),
            request_key="workspace-fixture",
            config_snapshot=snapshot,
            config_sha256=digest(snapshot),
        )
        run = Run(**attrs)
        s.add(run)
        s.flush()
        s.add(
            InventoryDaily(
                run_id=run.id,
                window_origin=D,
                item_id=item,
                date=D,
                policy_id=policy.id,
                forecast_as_of_date=D,
                opening_qty=7,
                receipts_qty=0,
                sales_qty=0,
                fulfilled_qty=0,
                shortage_qty=0,
                closing_qty=7,
                ss=2,
                rop_forecast=9,
                rop=20,
                target_stock=21,
                pending_qty=20 if pending else 0,
                inventory_position=27 if pending else 7,
                needs_replenishment=True,
                recommended_qty=0 if pending else 14,
                config_status="configured",
                is_simulated=True,
            )
        )
        for name, ordered, qty in [
            ("known", D - timedelta(days=3 if pending else 10), 20),
            ("future", D + timedelta(days=2), 50),
            ("past", D - timedelta(days=12), 5),
        ]:
            s.add(
                Replenishment(
                    run_id=run.id,
                    window_origin=D,
                    item_id=item,
                    policy_id=policy.id,
                    order_key=name,
                    ordered_on=ordered,
                    eta=ordered + timedelta(days=7),
                    ordered_qty=qty,
                    received_qty=qty,
                    status="received",
                    is_initial=False,
                    is_simulated=True,
                )
            )
        for alert_type, state in [
            ("depletion", "urgent"),
            ("below_rop", "pending_covers" if pending else "low_stock"),
        ]:
            s.add(
                Alert(
                    run_id=run.id,
                    window_origin=D,
                    item_id=item,
                    as_of_date=D,
                    alert_type=alert_type,
                    state=state,
                    predicted_depletion_date=D + timedelta(days=3)
                    if alert_type == "depletion"
                    else None,
                    actual_depletion_date=None,
                    is_evaluable=False,
                    explanation={},
                    is_simulated=True,
                )
            )
        return run.id, parent, item


def test_workspace_pending_counts_are_as_of_and_alert_items_not_double_counted(
    pg, tmp_path
):
    _, sessions = pg
    key, _, item = workspace_fixture(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        path = f"/api/v1/runs/{key}/workspace?as_of_date={D}"
        r = client.get(path)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["summary"]["on_hand_units"] == 7
        assert (
            data["summary"]["item_count"]
            == data["summary"]["low_stock_items"]
            == data["summary"]["urgent_items"]
            == 1
        )
        assert data["summary"]["replenish_items"] == 0 and data["attention"] == []
        assert (
            data["summary"]["incoming_lots"] == 1
            and data["summary"]["pending_units"] == 20
        )
        assert (
            data["incoming"][0]["ordered_qty"] == 20
        )  # Final status received must not hide this lot at D.
        assert data["route_stock"][0]["closing_qty"] == 7
        empty = client.get(path + "&item_id=999").json()
        assert (
            empty["summary"]["item_count"] == 0
            and empty["summary"]["on_hand_units"] is None
        )
        assert not empty["summary"]["inventory_available"] and not empty["incoming"]
        other = client.get(path + "&product_type=physical_SIM").json()
        assert not other["summary"]["inventory_available"]
        missing_day = client.get(
            f"/api/v1/runs/{key}/workspace?as_of_date={D + timedelta(days=1)}"
        ).json()
        assert missing_day["summary"]["on_hand_units"] is None
        assert missing_day["context"]["run_id"] == str(key)


def test_workspace_attention_and_guardrails(pg, tmp_path):
    _, sessions = pg
    key, parent, item = workspace_fixture(sessions, pending=False)
    with TestClient(create_app(settings(tmp_path))) as client:
        path = f"/api/v1/runs/{key}/workspace?as_of_date={D}"
        r = client.get(path).json()
        assert (
            r["summary"]["recommended_units"] == 14
            and r["summary"]["replenish_items"] == 1
        )
        assert r["attention"][0]["item_id"] == item and not r["incoming"]
        assert client.get(path + "&product_type=unknown").status_code == 422
        assert client.get(path + "&unknown=true").status_code == 422
        assert (
            client.get(f"/api/v1/runs/{parent}/workspace?as_of_date={D}").status_code
            == 409
        )
        with sessions.begin() as s:
            s.get(Run, key).status = "running"
        assert client.get(path).status_code == 409


def test_metric_split_is_filtered_before_pagination_and_export(pg, tmp_path):
    _, sessions = pg
    _, parent, _ = result_fixture(sessions)
    with sessions.begin() as s:
        r = s.get(Run, parent)
        r.result_summary = {
            "metrics": [
                dict(
                    destination_country="DemoLand",
                    carrier="DemoCarrier",
                    split="validation",
                    mape_positive_pct=3,
                )
            ]
            * 105
            + [
                dict(
                    destination_country="DemoLand",
                    carrier="DemoCarrier",
                    split="test",
                    mape_positive_pct=12,
                )
            ]
        }
    with TestClient(create_app(settings(tmp_path))) as client:
        path = f"/api/v1/runs/{parent}"
        r = client.get(path + "/metrics?split=test&page_size=100")
        assert r.status_code == 200 and r.json()["total"] == 1
        assert r.json()["items"][0]["mape_positive_pct"] == 12
        export = client.get(path + "/exports/metrics?split=test")
        assert export.status_code == 200 and "validation" not in export.text
