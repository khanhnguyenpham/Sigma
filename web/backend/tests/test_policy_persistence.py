"""Policy persistence on synthetic fixtures; migrations touch only sigma_m3_test."""
from copy import deepcopy
from datetime import timedelta
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, DataError

from core.hashes import digest
from core.run_context import snapshot_maps, required_run
from main import create_app
from models import Base
from modules.configuration.models import Policy, Scenario
from modules.configuration.schemas import POLICY_DEFAULTS, PolicyCreate, PolicyOverride
from modules.configuration.service import create_policy
from modules.inventory.simulation import pure_window
from modules.runs.models import Run
from modules.runs.schemas import RunCreate
from modules.runs.service import enqueue
from test_postgres_api import seed, settings, request, D
from test_results_api import result_fixture
from test_simulation import inputs, ORIGIN


def scenario_body(overrides):
    return dict(name="Synthetic policy settings", code="policy_settings", settings=dict(
        cover_days=7, safety_multiplier=1, policy_overrides=overrides,
        receipts_initial=[], receipts_declared=True,
    ))


@pytest.mark.parametrize("field,value", [
    ("safety_mode", "unknown"), ("rop_mode", "unknown"),
    ("safety_lookback_days", 6), ("safety_lookback_days", 91),
    ("safety_lookback_days", 28.5), ("safety_lookback_days", True),
    ("warning_horizon_days", 0), ("warning_horizon_days", 15),
    ("warning_horizon_days", 7.0), ("warning_horizon_days", False),
    ("safety_factor", -1), ("safety_factor", float("nan")),
    ("safety_factor", float("inf")), ("safety_factor", float("-inf")),
    ("safety_factor", True), ("safety_factor", "1"),
])
def test_policy_and_override_reject_invalid_parameters(field, value):
    body = request(1, 1).model_dump()
    with pytest.raises(ValidationError):
        PolicyCreate.model_validate({**body, field: value})
    with pytest.raises(ValidationError):
        PolicyOverride.model_validate(dict(item_id=1, **{field: value}))


def test_omitted_policy_defaults_and_partial_override_inheritance():
    p = request(1, 1)
    assert {k: getattr(p, k) for k in POLICY_DEFAULTS} == POLICY_DEFAULTS
    assert PolicyOverride(item_id=1).model_dump(exclude_none=True) == {"item_id": 1}
    assert PolicyOverride(item_id=1, safety_mode=None, safety_factor=0).model_dump(exclude_none=True) == {"item_id": 1, "safety_factor": 0}
    for field in POLICY_DEFAULTS:
        with pytest.raises(ValidationError):
            PolicyCreate.model_validate({**p.model_dump(), field: None})


def test_policy_http_versions_modes_intervals_and_safe_validation(pg, tmp_path):
    _, sessions = pg
    item, supplier, other = seed(sessions)
    with TestClient(create_app(settings(tmp_path))) as c:
        path = "/api/v1/supplier-item-policies"
        body = request(item, supplier).model_dump(mode="json")
        for field in POLICY_DEFAULTS:
            body.pop(field)
        first = c.post(path, json=body)
        assert first.status_code == 201
        assert {k: first.json()[k] for k in POLICY_DEFAULTS} == POLICY_DEFAULTS
        versions = [first.json()]
        for version, (safety, rop) in enumerate([
            ("days", "fixed"), ("volatility", "forecast"), ("volatility", "fixed"),
        ], 1):
            body.update(expected_version=version, effective_from=str(D + timedelta(days=version)),
                        supplier_id=other, safety_mode=safety, rop_mode=rop,
                        safety_lookback_days=7 if version == 1 else 90,
                        safety_factor=0 if version == 1 else 2.5,
                        warning_horizon_days=1 if version == 1 else 14)
            response = c.post(path, json=body)
            assert response.status_code == 201
            assert response.json()["version"] == version + 1
            assert {k: response.json()[k] for k in POLICY_DEFAULTS} == {k: body[k] for k in POLICY_DEFAULTS}
            versions.append(response.json())
            assert c.post(path, json=body).status_code == 409
        for index, policy in enumerate(versions):
            rows = c.get(path, params=dict(item_id=item, effective_on=str(D + timedelta(days=index)))).json()["items"]
            assert len(rows) == 1 and rows[0]["id"] == policy["id"]
            assert {k: rows[0][k] for k in POLICY_DEFAULTS} == {k: policy[k] for k in POLICY_DEFAULTS}
        for field, value in [("safety_mode", "PRIVATE_INVALID_SENTINEL"), ("safety_lookback_days", 6), ("safety_factor", -1), ("warning_horizon_days", 15), ("rop_mode", None)]:
            bad = c.post(path, json={**body, field: value})
            assert bad.status_code == 422
            assert bad.json()["error"]["code"] == "invalid_input"
            assert "PRIVATE_INVALID_SENTINEL" not in bad.text
        bad_scenario = scenario_body([dict(item_id=item, warning_horizon_days=0)])
        assert c.post("/api/v1/scenarios", json=bad_scenario).status_code == 422


def test_scenario_override_freezes_all_fields_and_keeps_old_runs(pg, tmp_path):
    _, sessions = pg
    source, forecast, item = result_fixture(sessions)
    with sessions.begin() as s:
        policy = create_policy(s, request(item, 1))
        policy.safety_factor = 2.5
    with TestClient(create_app(settings(tmp_path))) as c:
        partial = dict(item_id=item, safety_mode="volatility", rop_mode="fixed",
                       safety_lookback_days=90, warning_horizon_days=14, safety_factor=None)
        created = c.post("/api/v1/scenarios", json=scenario_body([partial]))
        assert created.status_code == 201
        scenario = created.json()
        assert "safety_factor" not in scenario["settings"]["policy_overrides"][0]
        body = dict(kind="stock_projection", source_import_run_id=str(source),
                    forecast_run_id=str(forecast), scenario_id=scenario["id"], as_of_date=str(D))
        response = c.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "frozen-policy"})
        assert response.status_code == 202
        key = uuid.UUID(response.json()["run_id"])
        with sessions() as s:
            run = s.get(Run, key)
            frozen = deepcopy(run.config_snapshot)
            checksum = run.config_sha256
            p = frozen["policies"][0]
            assert {k: p[k] for k in POLICY_DEFAULTS} == dict(
                safety_mode="volatility", rop_mode="fixed", safety_lookback_days=90,
                safety_factor=2.5, warning_horizon_days=14,
            )
            assert p["scenario_override"] is True
            assert frozen["scenario"]["settings"] == scenario["settings"]
            assert digest(frozen) == checksum
        # Version changes affect a later run only, never an existing snapshot.
        later = request(item, 2, 1, D + timedelta(days=1)).model_dump(mode="json")
        later.update(safety_factor=4, warning_horizon_days=1)
        assert c.post("/api/v1/supplier-item-policies", json=later).status_code == 201
        changed = scenario_body([dict(item_id=item, safety_factor=0)])
        new_scenario = c.post("/api/v1/scenarios", json=changed).json()
        assert new_scenario["version"] == 2
        assert c.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "frozen-policy"}).json()["run_id"] == str(key)
        with sessions() as s:
            old = s.get(Run, key)
            assert old.config_snapshot == frozen and old.config_sha256 == checksum
            assert s.get(Scenario, scenario["id"]).settings == scenario["settings"]
        body.update(scenario_id=new_scenario["id"], as_of_date=str(D + timedelta(days=1)))
        new = c.post("/api/v1/runs", json=body, headers={"Idempotency-Key": "new-policy"})
        assert new.status_code == 202
        with sessions() as s:
            run = s.get(Run, uuid.UUID(new.json()["run_id"]))
            p = next(p for p in run.config_snapshot["policies"] if p["version"] == 2)
            assert p["version"] == 2 and p["supplier_id"] == 2
            assert p["safety_factor"] == 0 and p["warning_horizon_days"] == 1
            assert p["safety_mode"] == "days" and p["rop_mode"] == "forecast"
        retroactive = {**later, "expected_version": 2, "effective_from": str(D + timedelta(days=1))}
        assert c.post("/api/v1/supplier-item-policies", json=retroactive).status_code == 409


def test_database_constraints_reject_invalid_policy_parameters(pg):
    engine, sessions = pg
    item, supplier, _ = seed(sessions)
    with sessions.begin() as s:
        key = create_policy(s, request(item, supplier)).id
    for field, value in [
        ("safety_mode", "bad"), ("rop_mode", "bad"),
        ("safety_lookback_days", 6), ("safety_lookback_days", 91),
        ("warning_horizon_days", 0), ("warning_horizon_days", 15),
        ("safety_factor", -1), ("safety_factor", float("nan")),
        ("safety_factor", float("inf")), ("safety_factor", float("-inf")),
        *[(k, None) for k in POLICY_DEFAULTS],
    ]:
        with pytest.raises((IntegrityError, DataError)):
            with engine.begin() as connection:
                connection.execute(Policy.__table__.update().where(Policy.id == key).values(**{field: value}))


def test_upgrade_preserves_legacy_snapshot_scenario_and_defaults(pg):
    engine, sessions = pg
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.attributes["database_url"] = str(engine.url.render_as_string(hide_password=False))
    # pg is guarded by conftest: destructive migration exercise is test DB only.
    command.downgrade(cfg, "0001_m3")
    try:
        item, supplier, _ = seed(sessions)
        with sessions.begin() as s:
            key = s.scalar(text("""INSERT INTO supplier_item_policies
                (item_id,supplier_id,version,effective_from,configured_rop_floor,moq,safety_days,is_assumed,assumption_source)
                VALUES (:item,:supplier,1,:day,100,50,2,true,'synthetic_legacy') RETURNING id"""),
                dict(item=item, supplier=supplier, day=D))
            scenario = Scenario(code="legacy", version=1, name="Legacy", assumption_version="synthetic",
                                settings=scenario_body([dict(item_id=item, moq=10)])["settings"])
            s.add(scenario)
            run, _ = enqueue(s, RunCreate(kind="source_import", source_key="orders_snapshot", as_of_date=D), "legacy")
            run.status = "complete"
            run.config_snapshot = {**run.config_snapshot, "warehouse_snapshot": [], "catalog_snapshot": [],
                "policies": [dict(id=key, item_id=item, supplier_id=supplier, version=1,
                    effective_from=str(D), effective_to=None, configured_rop_floor=100, moq=50, safety_days=2)]}
            run.config_sha256 = digest(run.config_snapshot)
            run.artifact_manifest = {"synthetic_legacy": "a" * 64}
            run_id = run.id
        with engine.connect() as connection:
            before = connection.execute(text("SELECT row_to_json(runs)::text FROM runs")).scalar_one()
            scenario_before = connection.execute(text("SELECT row_to_json(scenarios)::text FROM scenarios")).scalar_one()
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")
        with engine.connect() as connection:
            assert connection.execute(text("SELECT row_to_json(runs)::text FROM runs")).scalar_one() == before
            assert connection.execute(text("SELECT row_to_json(scenarios)::text FROM scenarios")).scalar_one() == scenario_before
            assert compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True, "compare_server_default": True}), Base.metadata) == []
        assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
        with sessions() as s:
            row = s.get(Policy, key)
            assert {k: getattr(row, k) for k in POLICY_DEFAULTS} == POLICY_DEFAULTS
            run = required_run(s, run_id, complete=True)
            frozen = deepcopy(run.config_snapshot)
            checksum = run.config_sha256
            interpreted = snapshot_maps(s, run)[2][key]
            assert {k: interpreted[k] for k in POLICY_DEFAULTS} == POLICY_DEFAULTS
            interpreted["safety_mode"] = "volatility"
            assert run.config_snapshot == frozen and digest(frozen) == checksum
            s.commit()
        with engine.connect() as connection:
            assert connection.execute(text("SELECT row_to_json(runs)::text FROM runs")).scalar_one() == before
    finally:
        command.upgrade(cfg, "head")


@pytest.mark.parametrize("safety,rop", [("days", "fixed"), ("volatility", "forecast"), ("volatility", "fixed")])
def test_persisted_modes_are_executable_after_step11(safety, rop):
    args = list(inputs())
    args[4][0].update(safety_mode=safety, rop_mode=rop)
    row = pure_window(*args, "stock_projection", ORIGIN, ORIGIN)["ledger"][0]
    assert row["ss"] == (20 if safety == "days" else 0)
    assert row["rop"] == (100 if rop == "fixed" else max(100, row["rop_forecast"]))
