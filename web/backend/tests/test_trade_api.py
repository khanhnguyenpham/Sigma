"""Stage 3 HTTP previews, scope/version races and frozen trade snapshots."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import uuid

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text

from core.errors import DomainError
from core.hashes import digest
from main import create_app
from modules.catalog.models import Item, Warehouse, ProviderProductNotice
from modules.catalog.schemas import SupplyChangeCreate
from modules.catalog.supply_service import create_supply_change
from modules.catalog.provider_service import create_provider_notice
from modules.catalog.provider import trade_state
from modules.configuration.service import create_policy
from modules.inventory.models import InventoryDaily
from modules.runs.models import Run
from modules.runs.verification import verify_run
from test_postgres_api import seed, settings, request, D
from test_results_api import result_fixture
from test_policy_persistence import scenario_body
from test_trade_lifecycle import migration_config
from test_workspace_api import workspace_fixture

ROOT = "/api/v1/provider-product-notices"
PROFILE = "internal_provider_trade_v2"


def catalog(sessions, parents=False):
    if parents:
        source, forecast, item = result_fixture(sessions)
        supplier = 1
    else:
        item, supplier, _ = seed(sessions)
        source = forecast = None
    with sessions.begin() as s:
        w = Warehouse(code="SECOND-W", destination_country="OtherMarket", carrier="DemoCarrier",
                      city="Second City", assumption_source="synthetic")
        s.add(w); s.flush()
        second = Item(warehouse_id=w.id, sku="DEMO-ESIM-01", product_type="eSIM", first_seen_date=D)
        outside = Item(warehouse_id=w.id, sku="DEMO-ESIM-01", product_type="physical_SIM", first_seen_date=D)
        s.add_all([second, outside]); s.flush()
        scope = dict(products=[dict(sku="DEMO-ESIM-01", product_type="eSIM",
            destination_countries=["DemoLand", "OtherMarket"], warehouse_ids=[1, w.id])])
        return dict(source=source, forecast=forecast, item=item, supplier=supplier,
                    members=[item, second.id], outside=outside.id, scope=scope)


def draft(data, **changes):
    return dict(dict(action="stop", supplier_id=data["supplier"], scope_definition=data["scope"],
        known_on=str(D), effective_on=str(D), reason="Declared provider simulation",
        source_description="Hypothetical provider notice, no source URL", expected_version=0), **changes)


def create_notice(client, body):
    preview = client.post(ROOT+"/preview", json=body)
    assert preview.status_code == 200, preview.text
    result = client.post(ROOT, json={**body, "preview_fingerprint": preview.json()["preview_fingerprint"]})
    assert result.status_code == 201, result.text
    return result.json(), preview.json()


def internal_body(**changes):
    return dict(dict(action="stop", known_on=str(D), effective_on=str(D),
                     reason="Internal simulation", expected_version=0), **changes)


def save_internal(client, item, body):
    preview = client.post(f"/api/v1/products/{item}/internal-stop-preview", json=body)
    assert preview.status_code == 200, preview.text
    result = client.post(f"/api/v1/products/{item}/supply-changes",
                        json={**body, "preview_fingerprint": preview.json()["preview_fingerprint"]})
    assert result.status_code == 201, result.text
    return result.json(), preview.json()


def follow_body(saved, action="resume_supply", **changes):
    return dict(dict(action=action, notice_id=saved["notice_id"], target_event_id=saved["event"]["id"],
        known_on=str(D), effective_on=str(D), expected_version=1, reason="Declared follow-up",
        source_description="Hypothetical follow-up"), **changes)


def save_follow(client, body):
    preview = client.post(ROOT+"/preview", json=body)
    assert preview.status_code == 200, preview.text
    payload = {k:v for k,v in body.items() if k not in {"action", "notice_id"}}
    payload["preview_fingerprint"] = preview.json()["preview_fingerprint"]
    endpoint = "cancel" if body["action"] == "cancel_stop" else "resume"
    response = client.post(f"{ROOT}/{body['notice_id']}/{endpoint}", json=payload)
    assert response.status_code == 201, response.text
    return response.json(), payload


def test_multiwarehouse_notice_filters_and_independent_rights(pg, tmp_path):
    _, sessions = pg
    data = catalog(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        body = draft(data)
        preview = client.post(ROOT+"/preview?page_size=1&page=2", json=body).json()
        assert preview["total"] == preview["scope_items"] == 2 and len(preview["items"]) == 1
        assert preview["scope_warehouses"] == 2 and preview["impact"]["stock_qty"] is None
        saved, _ = create_notice(client, body)
        assert saved["item_ids"] == data["members"]
        assert client.get(ROOT+"?page_size=1").json()["total"] == 1
        assert client.get(f"{ROOT}/{saved['notice_id']}/items?page_size=1&page=2&as_of_date={D}").json()["total"] == 2
        event = client.get(f"{ROOT}/{saved['notice_id']}/events").json()["items"][0]
        assert event["source_ref"] is None and event["is_assumed"] is True
        filtered = client.get(f"/api/v1/products?provider_status=stopped&sales_allowed=false&as_of_date={D}&page_size=1&page=2").json()
        assert filtered["total"] == 2 and len(filtered["items"]) == 1
        outside = client.get(f"/api/v1/products/{data['outside']}?as_of_date={D}").json()
        assert outside["sales_allowed"] and outside["replenishment_allowed"]
        first, _ = save_internal(client, data["item"], internal_body())
        _, opened = save_internal(client, data["item"], internal_body(action="resume", expected_version=1,
                                                    target_change_id=first["id"]))
        assert not opened["after"]["sales_allowed"] and not opened["after"]["replenishment_allowed"]
        save_internal(client, data["members"][1], internal_body())
        save_follow(client, follow_body(saved, effective_on=str(D+timedelta(days=4))))
        scheduled = client.get(f"{ROOT}/{saved['notice_id']}?as_of_date={D}").json()
        assert scheduled["state"]["provider_status"] == "scheduled_resume"
        later = client.get(f"/api/v1/products/{data['members'][1]}?as_of_date={D+timedelta(days=4)}").json()
        assert later["sales_allowed"] and not later["replenishment_allowed"]
        assert client.get(f"/api/v1/products?internal_status=stopped&provider_status=clear&as_of_date={D+timedelta(days=4)}").json()["total"] == 1


def test_cancel_is_not_resume_and_late_notice_does_not_rewrite_prior_dates(pg, tmp_path):
    _, sessions = pg
    data = catalog(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        saved, _ = create_notice(client, draft(data, effective_on=str(D+timedelta(days=7))))
        result, payload = save_follow(client, follow_body(saved, "cancel_stop",
            known_on=str(D+timedelta(days=1)), effective_on=str(D+timedelta(days=1))))
        assert result["version"] == 2
        assert client.post(f"{ROOT}/{saved['notice_id']}/cancel", json=payload).status_code == 409
        assert client.get(f"{ROOT}/{saved['notice_id']}?as_of_date={D}").json()["state"]["provider_status"] == "scheduled_stop"
        cancelled = client.get(f"{ROOT}/{saved['notice_id']}?as_of_date={D+timedelta(days=1)}").json()
        assert cancelled["state"]["provider_status"] == "clear" and cancelled["latest_action"] == "cancel_stop"
        late, _ = create_notice(client, draft(data, known_on=str(D+timedelta(days=2)), effective_on=str(D-timedelta(days=5))))
        assert client.get(f"/api/v1/products/{data['item']}?as_of_date={D+timedelta(days=1)}").json()["sales_allowed"]
        assert not client.get(f"/api/v1/products/{data['item']}?as_of_date={D+timedelta(days=2)}").json()["sales_allowed"]
        assert client.get(ROOT+"?status=stopped").status_code == 422
        assert client.get(ROOT+"?unknown_field=1").status_code == 422
        assert client.get(f"{ROOT}?status=stopped&as_of_date={D+timedelta(days=2)}&product_type=eSIM&warehouse_id=1").json()["total"] == 1
        assert client.get(f"{ROOT}?sku=outside&as_of_date={D}").json()["total"] == 0
        assert client.get(f"{ROOT}/999999").status_code == 404


@pytest.mark.parametrize("change", [
    dict(reason=" "), dict(source_description=" "), dict(expected_version=True),
    dict(source_ref="javascript:private-sentinel"), dict(extra="private-sentinel"),
    dict(scope_definition={"products": [{"sku":"DEMO-ESIM-01","product_type":"eSIM",
        "destination_countries":["DemoLand"],"warehouse_ids":[True]}]}),
])
def test_payload_validation_and_no_private_echo(pg, tmp_path, change):
    _, sessions = pg
    data = catalog(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        result = client.post(ROOT+"/preview", json=draft(data, **change))
        assert result.status_code == 422, result.text
        assert "private-sentinel" not in result.text


def test_stale_preview_and_concurrent_create_do_not_duplicate_notice(pg, tmp_path):
    _, sessions = pg
    data = catalog(sessions)
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        body = draft(data)
        preview = client.post(ROOT+"/preview", json=body).json()
        client.patch("/api/v1/warehouses/1", json={"city":"Updated City","expected_version":1})
        stale = client.post(ROOT, json={**body,"preview_fingerprint":preview["preview_fingerprint"]})
        assert stale.status_code == 409 and stale.json()["error"]["code"] == "preview_stale"
        fresh = client.post(ROOT+"/preview", json=body).json()
    def create(_):
        with TestClient(create_app(cfg)) as client:
            response = client.post(ROOT, json={**body,"preview_fingerprint":fresh["preview_fingerprint"]})
            return response.status_code
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(create, range(2))) == [201,409]
    with sessions() as s:
        assert s.scalar(select(func.count()).select_from(ProviderProductNotice)) == 1


def test_internal_preview_stales_when_provider_constraint_changes(pg, tmp_path):
    _, sessions = pg
    data = catalog(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        body = internal_body()
        preview = client.post(f"/api/v1/products/{data['item']}/internal-stop-preview", json=body).json()
        create_notice(client, draft(data))
        response = client.post(f"/api/v1/products/{data['item']}/supply-changes",
                               json={**body,"preview_fingerprint":preview["preview_fingerprint"]})
        assert response.status_code == 409
        assert client.post(f"/api/v1/products/{data['item']}/supply-changes", json=body).status_code == 422


def test_preview_impact_uses_frozen_rows_and_keeps_missing_trade_quantities_null(pg, tmp_path):
    _, sessions = pg
    key, _, item = workspace_fixture(sessions)
    body = internal_body(impact_run_id=str(key), impact_as_of_date=str(D))
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post(f"/api/v1/products/{item}/internal-stop-preview", json=body)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["impact"]["stock_qty"] == data["stock_qty"] == 7
        assert data["impact"]["pending_qty"] == 20
        assert data["impact"]["sellable_qty"] is None and data["impact"]["blocked_qty"] is None
        assert data["before"]["sales_allowed"] and data["after"]["sales_allowed"]
        assert not data["after"]["replenishment_allowed"] and data["existing_lots_kept"]
        before_hash = data["preview_fingerprint"]
        body["impact_as_of_date"] = str(D+timedelta(days=30))
        missing = client.post(f"/api/v1/products/{item}/internal-stop-preview", json=body).json()
        assert missing["impact"]["stock_qty"] is None
        assert missing["impact"]["pending_qty"] is None
        assert missing["preview_fingerprint"] != before_hash


def configured_run(client, sessions, data, kind="stock_projection", key="trade", profile=PROFILE):
    with sessions.begin() as s:
        create_policy(s, request(data["item"], data["supplier"]))
    scenario = client.post("/api/v1/scenarios", json=scenario_body([])).json()
    body = dict(kind=kind, as_of_date=str(D), source_import_run_id=str(data["source"]),
                forecast_run_id=str(data["forecast"]), scenario_id=scenario["id"])
    if profile:
        body["trade_lifecycle_profile"] = profile
    if kind != "stock_projection":
        body.update(period_start=str(D+timedelta(days=1)), period_end=str(D+timedelta(days=30)))
    response = client.post("/api/v1/runs", json=body, headers={"Idempotency-Key":key})
    return response, body


@pytest.mark.parametrize("kind,included", [("stock_projection",False),("alert_replay",False),("policy_replay",True)])
def test_snapshot_cutoffs_full_scope_and_idempotence_after_new_live_events(pg, tmp_path, kind, included):
    _, sessions = pg
    data = catalog(sessions, parents=True)
    with sessions() as s:
        old = {r.id:(deepcopy(r.config_snapshot),r.config_sha256) for r in s.scalars(select(Run))}
    with TestClient(create_app(settings(tmp_path))) as client:
        saved, _ = create_notice(client, draft(data, known_on=str(D+timedelta(days=15)),
                                               effective_on=str(D+timedelta(days=8))))
        save_internal(client, data["item"], internal_body(known_on=str(D+timedelta(days=15)),
                                                        effective_on=str(D+timedelta(days=15))))
        response, body = configured_run(client, sessions, data, kind)
        assert response.status_code == 202, response.text
        key = uuid.UUID(response.json()["run_id"])
        with sessions() as s:
            run = s.get(Run,key); snap=deepcopy(run.config_snapshot); checksum=run.config_sha256
        assert snap["trade_lifecycle_profile"] == PROFILE and "supply_lifecycle_profile" not in snap
        assert bool(snap["provider_notice_snapshot"]) == bool(snap["internal_supply_snapshot"]) == included
        assert digest(snap) == checksum and snap["trade_rules"]["calendar"] == "UTC"
        if included:
            assert snap["provider_notice_snapshot"][0]["item_ids"] == data["members"]
            assert len(snap["provider_notice_snapshot"][0]["item_snapshot"]) == 2
            assert trade_state(snap["internal_supply_snapshot"],snap["provider_notice_snapshot"],data["item"],D)["sales_allowed"]
        save_follow(client, follow_body(saved, known_on=str(D+timedelta(days=16)), effective_on=str(D+timedelta(days=16))))
        retried = client.post("/api/v1/runs", json=body, headers={"Idempotency-Key":"trade"})
        assert retried.status_code == 200 and retried.json()["run_id"] == str(key)
        with sessions() as s:
            assert s.get(Run,key).config_snapshot == snap and s.get(Run,key).config_sha256 == checksum
            assert {r.id:(r.config_snapshot,r.config_sha256) for r in s.scalars(select(Run).where(Run.id.in_(old)))} == old


def test_new_profile_guards_worker_verifier_and_legacy_bypass(pg, tmp_path):
    _, sessions = pg
    data = catalog(sessions, parents=True)
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        create_notice(client, draft(data))
        response, body = configured_run(client,sessions,data,profile=None)
        assert response.status_code == 409 and response.json()["error"]["code"] == "trade_profile_required"
        body["trade_lifecycle_profile"] = PROFILE
        response = client.post("/api/v1/runs",json=body,headers={"Idempotency-Key":"new-profile"})
        assert response.status_code == 202, response.text
        key = uuid.UUID(response.json()["run_id"])
        from worker import serve
        serve(cfg, once=True)
        with sessions() as s:
            run = s.get(Run,key)
            assert run.status == "failed" and run.error_code == "stage_not_implemented"
            assert s.scalar(select(func.count()).select_from(InventoryDaily).where(InventoryDaily.run_id==key)) == 0
        with sessions.begin() as s:
            s.get(Run,key).status = "complete"
        with pytest.raises(DomainError) as exc:
            verify_run(cfg,sessions,key)
        assert exc.value.code == "stage_not_implemented"
        assert client.get(f"/api/v1/runs/{key}/inventory").status_code == 409


def test_schema0007_keeps_old_reads_and_rejects_new_operations(pg, tmp_path):
    engine, sessions = pg
    data = catalog(sessions)
    cfg=migration_config(engine)
    command.downgrade(cfg,"0007_supply_lifecycle")
    try:
        with TestClient(create_app(settings(tmp_path))) as client:
            row=client.get(f"/api/v1/products/{data['item']}?as_of_date={D}").json()
            assert row["trade_schema_ready"] is False and row["sales_allowed"] is None
            assert client.get(f"/api/v1/products?provider_status=clear&as_of_date={D}").status_code==503
            assert client.get(ROOT).status_code==503
            assert client.post(ROOT+"/preview",json=draft(data)).status_code==503
            assert client.post(f"/api/v1/products/{data['item']}/internal-stop-preview",json=internal_body()).status_code==503
            assert client.post(f"/api/v1/products/{data['item']}/supply-changes",json=internal_body()).status_code==503
    finally:
        command.upgrade(cfg,"head")


def test_snapshot_waits_for_atomic_internal_and_provider_transaction(pg, tmp_path):
    _, sessions = pg
    data = catalog(sessions, parents=True)
    cfg = settings(tmp_path)
    with sessions.begin() as s:
        create_policy(s, request(data["item"], data["supplier"]))
    with TestClient(create_app(cfg)) as client:
        scenario = client.post("/api/v1/scenarios", json=scenario_body([])).json()
    body = dict(kind="stock_projection", as_of_date=str(D), source_import_run_id=str(data["source"]),
                forecast_run_id=str(data["forecast"]), scenario_id=scenario["id"], trade_lifecycle_profile=PROFILE)
    def enqueue():
        with TestClient(create_app(cfg)) as client:
            return client.post("/api/v1/runs", json=body, headers={"Idempotency-Key":"atomic-snapshot"})
    with ThreadPoolExecutor(1) as pool:
        with sessions.begin() as s:
            event = {k:v for k,v in draft(data).items() if k not in {"supplier_id","scope_definition","expected_version"}}
            create_provider_notice(s, supplier_id=data["supplier"], scope_definition=data["scope"],
                                   expected_version=0, **event)
            create_supply_change(s, data["item"], SupplyChangeCreate(**internal_body()), minimum_notice_days=0)
            future = pool.submit(enqueue)
        response = future.result(timeout=15)
    assert response.status_code == 202, response.text
    with sessions() as s:
        snap = s.get(Run,uuid.UUID(response.json()["run_id"])).config_snapshot
    assert len(snap["internal_supply_snapshot"]) == len(snap["provider_notice_snapshot"]) == 1


def test_trade_profile_cannot_be_used_on_source_or_forecast(pg, tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/v1/runs", json=dict(kind="source_import", as_of_date=str(D),
            source_key="orders_snapshot", trade_lifecycle_profile=PROFILE), headers={"Idempotency-Key":"bad-profile"})
        assert response.status_code == 422
