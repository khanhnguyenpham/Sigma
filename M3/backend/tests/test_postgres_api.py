from concurrent.futures import ThreadPoolExecutor
from datetime import date
import os, uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, inspect
from sqlalchemy.exc import IntegrityError, DataError
from sigma_m3.main import create_app
from sigma_m3.models import (
    Base,
    Warehouse,
    Item,
    Supplier,
    Policy,
    Run,
    RouteForecast,
    DailySales,
    Replenishment,
    InventoryEvent,
)
from sigma_m3.schemas import PolicyCreate, RunCreate
from sigma_m3.services.catalog import create_policy
from sigma_m3.services.runs import enqueue
from sigma_m3.settings import Settings
from sigma_m3.errors import DomainError
from sigma_m3.worker import serve

D = date(2025, 10, 31)


def seed(sessions):
    with sessions.begin() as s:
        w = Warehouse(
            code="DEMO-W1",
            destination_country="DemoLand",
            carrier="DemoCarrier",
            city="Demo City",
            assumption_source="synthetic_fixture",
        )
        a = Supplier(
            code="DEMO-S1",
            display_name="Demo supplier",
            assumption_source="synthetic_fixture",
        )
        b = Supplier(
            code="DEMO-S2",
            display_name="Other supplier",
            assumption_source="synthetic_fixture",
        )
        s.add_all([w, a, b])
        s.flush()
        item = Item(
            warehouse_id=w.id,
            sku="DEMO-ESIM-01",
            product_type="eSIM",
            first_seen_date=date(2024, 1, 1),
        )
        s.add(item)
        s.flush()
        return item.id, a.id, b.id


def request(item, supplier, version=0, start=D):
    return PolicyCreate(
        item_id=item,
        supplier_id=supplier,
        effective_from=start,
        configured_rop_floor=100,
        moq=50,
        safety_days=2,
        expected_version=version,
    )


def settings(tmp_path):
    return Settings(os.environ["M3_TEST_DATABASE_URL"], tmp_path, tmp_path / "outputs")


def test_real_postgres_migration_and_role(pg):
    engine, _ = pg
    assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {
        "alembic_version"
    }
    with engine.connect() as c:
        assert c.scalar(text("SHOW server_version")).startswith("18.")
        assert (
            c.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user"))
            is False
        )


def test_policy_version_intervals_across_suppliers(pg):
    _, sessions = pg
    i, a, b = seed(sessions)
    with sessions.begin() as s:
        first = create_policy(s, request(i, a))
    with sessions.begin() as s:
        second = create_policy(s, request(i, b, 1, date(2025, 11, 7)))
    with sessions() as s:
        assert s.get(Policy, first.id).effective_to == date(2025, 11, 7)
        assert s.get(Policy, second.id).supplier_id == b
    with pytest.raises(DomainError, match="reload"):
        with sessions.begin() as s:
            create_policy(s, request(i, a, 1, date(2025, 11, 8)))
    with pytest.raises(DomainError, match="overlap"):
        with sessions.begin() as s:
            create_policy(s, request(i, a, 2, date(2025, 11, 6)))


def test_concurrent_policy_edits_one_wins(pg):
    _, sessions = pg
    i, a, b = seed(sessions)

    def save(supplier):
        try:
            with sessions.begin() as s:
                create_policy(s, request(i, supplier))
            return "created"
        except DomainError as exc:
            return exc.code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(save, [a, b]))
    assert sorted(results) == ["created", "version_conflict"]
    with sessions() as s:
        assert len(s.scalars(select(Policy)).all()) == 1


def test_frozen_run_prevents_retroactive_policy_close(pg):
    _, sessions = pg
    i, a, b = seed(sessions)
    with sessions.begin() as s:
        p = create_policy(s, request(i, a))
        r, _ = enqueue(
            s,
            RunCreate(
                kind="source_import",
                source_key="orders_snapshot",
                as_of_date="2025-12-31",
            ),
            "frozen",
        )
        r.config_snapshot = {**r.config_snapshot, "policy_ids": [p.id]}
    with pytest.raises(DomainError, match="frozen"):
        with sessions.begin() as s:
            create_policy(s, request(i, b, 1, date(2025, 11, 7)))


def test_database_blocks_nan_infinity_and_missing_actual(pg):
    _, sessions = pg
    seed(sessions)
    with sessions.begin() as s:
        r, _ = enqueue(
            s,
            RunCreate(kind="source_import", source_key="orders_snapshot", as_of_date=D),
            "data-guard",
        )
        key = r.id
    for value in [float("nan"), float("inf"), -1.0]:
        with pytest.raises((IntegrityError, DataError)):
            with sessions.begin() as s:
                s.add(
                    RouteForecast(
                        run_id=key,
                        warehouse_id=1,
                        as_of_date=D,
                        block=1,
                        window_start=date(2025, 11, 1),
                        target_date=date(2025, 11, 7),
                        forecast_qty=value,
                        actual_available=False,
                        family="synthetic",
                        model_id="fixture",
                        selection_basis="injected_fixture",
                    )
                )
    with pytest.raises(IntegrityError):
        with sessions.begin() as s:
            s.add(
                DailySales(
                    source_import_run_id=key,
                    item_id=1,
                    date=D,
                    sales_qty=0,
                    order_count=0,
                    actual_available=False,
                )
            )


def test_api_health_catalog_validation_and_queue(pg, tmp_path):
    _, sessions = pg
    seed(sessions)
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.get("/api/v1/health").json()["database"] == "reachable"
        assert client.get("/api/v1/items?warehouse_id=1").json()["total"] == 1
        assert client.get("/api/v1/items?page_size=101").status_code == 422
        body = {
            "kind": "source_import",
            "source_key": "orders_snapshot",
            "as_of_date": "2025-12-31",
        }
        first = client.post(
            "/api/v1/runs", json=body, headers={"Idempotency-Key": "same"}
        )
        assert first.status_code == 202
        second = client.post(
            "/api/v1/runs", json=body, headers={"Idempotency-Key": "same"}
        )
        assert (
            second.status_code == 200
            and second.json()["run_id"] == first.json()["run_id"]
        )
        conflict = client.post(
            "/api/v1/runs",
            json={**body, "as_of_date": "2025-11-30"},
            headers={"Idempotency-Key": "same"},
        )
        assert (
            conflict.status_code == 409
            and conflict.json()["error"]["code"] == "idempotency_conflict"
        )
        path = first.json()["status_url"]
        assert client.get(path).json()["status"] == "queued"
        assert client.get(path + "/summary").status_code == 409
        assert client.get("/api/v1/runs/" + str(uuid.uuid4())).status_code == 404
        invalid = client.post(
            "/api/v1/runs",
            json={**body, "source_key": "PRIVATE_SECRET_PATH"},
            headers={"Idempotency-Key": "invalid"},
        )
        assert invalid.status_code == 422 and "PRIVATE_SECRET_PATH" not in invalid.text


def test_api_policy_and_extra_lead_time_rejected(pg, tmp_path):
    _, sessions = pg
    i, a, _ = seed(sessions)
    body = request(i, a).model_dump(mode="json")
    with TestClient(create_app(settings(tmp_path))) as client:
        assert (
            client.post(
                "/api/v1/supplier-item-policies", json={**body, "lead_time_days": 3}
            ).status_code
            == 422
        )
        assert (
            client.post("/api/v1/supplier-item-policies", json=body).status_code == 201
        )
        assert (
            client.post("/api/v1/supplier-item-policies", json=body).status_code == 409
        )


def test_worker_lock_and_restart_not_false_complete(pg, tmp_path):
    engine, sessions = pg
    with sessions.begin() as s:
        r, _ = enqueue(
            s,
            RunCreate(kind="source_import", source_key="orders_snapshot", as_of_date=D),
            "interrupted",
        )
        r.status = "running"
        key = r.id
    from sigma_m3.worker import LOCK_ID

    with engine.connect() as lock:
        lock.execute(text("SELECT pg_advisory_lock(:key)"), {"key": LOCK_ID})
        try:
            with pytest.raises(DomainError, match="already active"):
                serve(settings(tmp_path), once=True)
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_ID})
    assert serve(settings(tmp_path), once=True) is None
    with sessions() as s:
        r = s.get(Run, key)
        assert (r.status, r.error_code) == ("failed", "interrupted")


def test_concurrent_idempotency_does_not_duplicate_run(pg):
    _, sessions = pg
    body = RunCreate(kind="source_import", source_key="orders_snapshot", as_of_date=D)

    def queue(_):
        with sessions.begin() as s:
            return enqueue(s, body, "concurrent")[0].id

    with ThreadPoolExecutor(2) as pool:
        keys = list(pool.map(queue, range(2)))
    assert keys[0] == keys[1]
    with sessions() as s:
        assert len(s.scalars(select(Run)).all()) == 1


def test_receipt_transaction_is_exactly_once_under_concurrency(pg):
    _, sessions = pg
    i, a, _ = seed(sessions)
    with sessions.begin() as s:
        policy = create_policy(s, request(i, a))
        run, _ = enqueue(
            s,
            RunCreate(kind="source_import", source_key="orders_snapshot", as_of_date=D),
            "receipt",
        )
        order = Replenishment(
            run_id=run.id,
            window_origin=D,
            item_id=i,
            policy_id=policy.id,
            order_key="synthetic-lot",
            ordered_on=D,
            eta=date(2025, 11, 7),
            ordered_qty=50,
            received_qty=0,
            status="ordered",
            is_initial=False,
            is_simulated=True,
        )
        s.add(order)
        s.flush()
        key = order.id
    from sigma_m3.services.receipts import receive_due

    with pytest.raises(DomainError, match="exact ETA"):
        with sessions.begin() as s:
            receive_due(s, key, date(2025, 11, 6), 80, 1)

    def receive(_):
        with sessions.begin() as s:
            event = receive_due(s, key, date(2025, 11, 7), 80, 1)
            return event.id if event else None

    with ThreadPoolExecutor(2) as pool:
        out = list(pool.map(receive, range(2)))
    assert sum(value is not None for value in out) == 1
    with sessions() as s:
        events = s.scalars(select(InventoryEvent)).all()
        assert len(events) == 1 and events[0].balance_after == 130
        assert s.get(Replenishment, key).received_qty == 50
