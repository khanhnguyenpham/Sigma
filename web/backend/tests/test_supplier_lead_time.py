"""Per-supplier lead time in the simulation tool; synthetic data on real PostgreSQL."""
import math
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from main import create_app
from modules.auth.schemas import UserCreate
from modules.auth.service import create_user
from modules.configuration.models import Policy
from modules.inventory.service import PolicyValues, eta, lead_for, recommend
from modules.operations.models import SupplierSettings
from modules.purchasing.models import Replenishment
from modules.runs.models import Run
from test_configurable_inventory import F, enqueue_fixture, worker_fixture
from test_postgres_api import D, request, settings
from worker import serve


def test_lead_time_drives_rop_target_eta_and_defaults_to_l7():
    policy = PolicyValues(0, 1, 1)
    default, short = recommend(F, 0, 0, policy), recommend(F, 0, 0, policy, lead=3)
    assert default == recommend(F, 0, 0, policy, lead=7)
    ss = math.ceil(sum(F) / len(F))
    assert short["rop_forecast"] == math.ceil(sum(F[:3]) + ss) and short["target_stock"] == short["rop"] + F[3]
    assert eta(date(2026, 1, 1), 10) == date(2026, 1, 11) and eta(date(2026, 1, 1)) == date(2026, 1, 8)
    assert lead_for(None, 4) == lead_for({"4": 7}, 4) == 7 and lead_for({"4": 5}, 4) == 5


def set_lead(sessions, supplier_id, days):
    with sessions.begin() as s:
        admin = s.scalar(select(SupplierSettings.updated_by).limit(1)) or create_user(
            s, UserCreate(username="lead-admin", display_name="Lead", password="Synthetic-only-Password-2026", role="admin")).id
        row = s.get(SupplierSettings, supplier_id)
        if row:
            row.lead_time_days, row.version = days, row.version + 1
        else:
            s.add(SupplierSettings(supplier_id=supplier_id, lead_time_days=days, version=1, updated_by=admin))


def test_new_run_freezes_supplier_lead_time_for_every_item_of_that_carrier(pg, tmp_path):
    _, sessions = pg
    source, forecast, item = worker_fixture(sessions, tmp_path)
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        with sessions() as s:
            supplier = s.scalar(select(Policy.supplier_id).where(Policy.item_id == item)) or 1
        set_lead(sessions, supplier, 4)
        key = enqueue_fixture(client, source, forecast, item, "days", "forecast", "policy_replay", legacy=False)
        with sessions() as s:
            run = s.get(Run, key)
            policy_supplier = run.config_snapshot["policies"][0]["supplier_id"]
            assert run.config_snapshot["supplier_lead_times"] == {str(policy_supplier): 4 if policy_supplier == supplier else 7}
        set_lead(sessions, policy_supplier, 9)  # A later edit never rewrites the queued run.
        assert serve(cfg, once=True) == key
        with sessions() as _s: assert _s.get(Run, key).status == 'complete'
        with sessions() as s:
            orders = s.scalars(select(Replenishment).where(Replenishment.run_id == key, Replenishment.is_initial.is_(False))).all()
            assert orders and all((o.eta - o.ordered_on).days == 4 for o in orders)
        rows = client.get(f"/api/v1/runs/{key}/inventory?page_size=100").json()["items"]
        assert all(r["eta_if_ordered"] == str(date.fromisoformat(r["date"]) + timedelta(days=4)) for r in rows if r["recommended_qty"])
        assert client.get(f"/api/v1/runs/{key}/snapshot").json()["parameters"]["supplier_lead_times"] == {str(policy_supplier): 4}


def test_lead_time_beyond_h14_is_rejected_before_queueing(pg, tmp_path):
    _, sessions = pg
    source, forecast, item = worker_fixture(sessions, tmp_path)
    with TestClient(create_app(settings(tmp_path))) as client:
        policy = request(item, 1).model_dump(mode="json")
        policy.update(configured_rop_floor=10, fixed_order_qty=5)
        assert client.post("/api/v1/supplier-item-policies", json=policy).status_code == 201
        set_lead(sessions, policy["supplier_id"], 14)
        scenario = client.post("/api/v1/scenarios", json=dict(name="Lead", code="lead", settings=dict(
            cover_days=7, safety_multiplier=1.5, receipts_declared=True, receipts_initial=[], policy_overrides=[]))).json()
        response = client.post("/api/v1/runs", headers={"Idempotency-Key": "lead-too-long"}, json=dict(kind="stock_projection",
            source_import_run_id=str(source), forecast_run_id=str(forecast), scenario_id=scenario["id"], as_of_date=str(D)))
        assert response.status_code == 409 and response.json()["error"]["code"] == "lead_time_exceeds_forecast"
        with sessions() as s:
            assert s.scalar(select(Run.id).where(Run.kind == "stock_projection")) is None
