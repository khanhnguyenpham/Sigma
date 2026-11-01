"""Distinct assumed locations with stable routes and immutable run snapshots."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from core.errors import DomainError
from core.hashes import digest
from main import create_app
from modules.catalog.locations import COUNTRY_CITIES, ROUTE_CITIES, display_warehouse, seed_cities
from modules.catalog.models import Supplier, Warehouse
from modules.catalog.service import rename_seed_cities
from modules.runs.models import Run
from test_postgres_api import D, settings
from test_workspace_api import workspace_fixture


def test_seed_locations_are_stable_and_require_distinct_configuration():
    routes = [("Australia", "Optus"), ("Australia", "Telstra"), ("Singapore", "M1"),
              ("Singapore", "Singtel"), ("Singapore", "StarHub"), ("Hong Kong", "3HK"),
              ("Hong Kong", "CSL"), ("Hong Kong", "SmarTone")]
    cities = seed_cities(routes)
    assert len(set(cities.values())) == len(routes)
    assert cities[("Australia", "Optus")] == "Sydney"
    assert cities[("Australia", "Telstra")] == "Melbourne"
    assert seed_cities(reversed(routes)) == cities
    assert seed_cities([("Australia", "Telstra")])[("Australia", "Telstra")] == "Melbourne"
    for missing in [[("Unknown", "Carrier")], [("Australia", "Optus"), ("Australia", "New carrier")]]:
        with pytest.raises(DomainError) as error:
            seed_cities(missing)
        assert error.value.code == "missing_partner_config"
    frozen = dict(destination_country="Australia", carrier="Telstra", city="Sydney", is_assumed=True)
    assert display_warehouse(frozen)["city"] == "Melbourne" and frozen["city"] == "Sydney"
    assert display_warehouse({**frozen, "city": "Custom City"})["city"] == "Custom City"
    assert display_warehouse({**frozen, "is_assumed": False})["city"] == "Sydney"


def test_catalog_seed_correction_is_previewable_idempotent_and_preserves_other_fields(pg):
    _, sessions = pg
    with sessions.begin() as session:
        for index, ((country, carrier), city) in enumerate(ROUTE_CITIES.items(), 1):
            session.add(Supplier(carrier=carrier))
            session.flush()
            session.add(Warehouse(code=f"SYN-{index}", destination_country=country, carrier=carrier,
                city=COUNTRY_CITIES[country], assumption_source="route_city_seed_v1"))
    with sessions.begin() as session:
        rows = session.scalars(select(Warehouse).order_by(Warehouse.id)).all()
        before = [{c.name: getattr(w, c.name) for c in Warehouse.__table__.columns} for w in rows]
        assert rename_seed_cities(session)["renamed"] == len(ROUTE_CITIES)
        assert [w.city for w in rows] == [w["city"] for w in before]
        assert rename_seed_cities(session, apply=True)["distinct_locations"] == len(rows)
        for old, row in zip(before, rows):
            assert row.city == ROUTE_CITIES[(row.destination_country, row.carrier)]
            assert row.version == old["version"] + 1
            assert row.assumption_source == "route_city_seed_v2"
            for name in old.keys() - {"city", "version", "assumption_source"}:
                assert getattr(row, name) == old[name]
        assert rename_seed_cities(session, apply=True)["renamed"] == 0


def test_legacy_run_names_match_catalog_workspace_forecasts_and_csv_without_rewriting(pg, tmp_path):
    _, sessions = pg
    key, forecast, _ = workspace_fixture(sessions, pending=False)
    with sessions.begin() as session:
        for run in session.scalars(select(Run).order_by(Run.created_at)):
            snapshot = deepcopy(run.config_snapshot)
            snapshot["warehouse_snapshot"][0].update(destination_country="Australia", carrier="Telstra",
                                                       city="Sydney", is_assumed=True)
            snapshot["catalog_snapshot"][0].update(destination_country="Australia", carrier="Telstra")
            for parent_id, name in [(run.source_import_run_id, "source_parent_config_sha256"),
                                    (run.forecast_run_id, "forecast_parent_config_sha256")]:
                if parent_id and name in snapshot:
                    snapshot[name] = session.get(Run, parent_id).config_sha256
            run.config_snapshot = snapshot
            run.config_sha256 = digest(snapshot)
        before = {run.id: (deepcopy(run.config_snapshot), run.config_sha256) for run in session.scalars(select(Run))}
    with TestClient(create_app(settings(tmp_path))) as client:
        catalog = client.get(f"/api/v1/warehouses?run_id={key}")
        assert catalog.status_code == 200, catalog.text
        assert catalog.json()["items"][0]["city"] == "Melbourne"
        path = f"/api/v1/runs/{key}"
        stock = client.get(path + f"/workspace?as_of_date={D}").json()
        assert stock["warehouse_stock"][0]["city"] == "Melbourne"
        assert stock["summary"]["on_hand_units"] == 7 and stock["summary"]["recommended_units"] == 14
        assert client.get(path + "/inventory").json()["items"][0]["city"] == "Melbourne"
        assert "Melbourne" in client.get(path + "/exports/inventory_daily").text
        assert client.get(f"/api/v1/runs/{forecast}/forecasts/routes").json()["items"][0]["city"] == "Melbourne"
        assert client.get(f"/api/v1/runs/{forecast}/forecasts/items?aggregate=route_day").json()["items"][0]["city"] == "Melbourne"
    with sessions() as session:
        for run in session.scalars(select(Run)):
            assert (run.config_snapshot, run.config_sha256) == before[run.id]
