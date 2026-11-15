from datetime import date
from types import SimpleNamespace
from modules.runs.snapshot import snapshot_view


def run(snapshot):
    return SimpleNamespace(id="synthetic", kind="stock_projection", status="complete",
        as_of_date=date(2025, 10, 31), period_start=None, period_end=None,
        source_import_run_id="source", forecast_run_id="forecast", created_at=None,
        config_version="v1", assumption_version="assumed", target_version="sales",
        config_snapshot=snapshot)


def test_snapshot_whitelists_business_fields_and_never_returns_private_config():
    source = dict(database_url="private-value", source_sha256="private-hash", private_path="private-file",
        scenario=dict(id=2, name="Frozen", version=1, token="secret", settings=dict(
            cover_days=7, safety_multiplier=0, credentials="secret",
            receipts_initial=[dict(item_id=1, ordered_qty=0, eta="2025-11-07", password="secret")],
            supply_schedule=dict(internal_stops=[dict(item_id=1, known_on="2025-10-31", effective_on="2025-11-05", reason="demo", secret="private")]))),
        policies=[dict(item_id=1, fixed_order_qty=15, database_url="secret")],
        catalog_snapshot=[dict(item_id=1, sku="SIM-A", product_type="physical_SIM", customer_id="private")],
        receiving_warehouse_snapshot=[dict(item_id=1, receiving_warehouse_id=3)])
    result = snapshot_view(run(source))
    assert result['parameters']['safety_multiplier'] == 0
    assert result['policies']['items'][0]['sku'] == 'SIM-A'
    assert result['policies']['items'][0]['receiving_warehouse_id'] == 3
    assert result['receipts_initial'][0]['ordered_qty'] == 0
    text = repr(result)
    for private in ('database_url', 'source_sha256', 'private_path', 'customer_id', 'credentials', 'password', 'token', 'secret'):
        assert private not in text
    assert source['scenario']['settings']['credentials'] == 'secret'


def test_snapshot_pages_policy_rows_and_reads_historical_stock_basis():
    snapshot = dict(initial_stock_fallback_days=90,
        policies=[dict(item_id=i, fixed_order_qty=5) for i in range(27)])
    result = snapshot_view(run(snapshot), page=2, page_size=25)
    # Legacy 90 days is a fallback only when the observed 28-day sum is zero.
    assert result['parameters']['initial_stock_history_days'] == 28
    assert result['parameters']['zero_sales_fallback_days'] == 90
    assert result['policies']['total'] == 27
    assert [row['item_id'] for row in result['policies']['items']] == [25, 26]
    assert snapshot_view(run(snapshot), page=3, page_size=25)['policies']['items'] == []


def test_legacy_snapshot_without_optional_sections_has_explicit_empty_lists():
    result = snapshot_view(run({}))
    assert result['scenario'] == {}
    assert result['parameters']['zero_sales_fallback_days'] is None
    assert result['policies']['items'] == []
    assert result['supply_schedule'] == {'internal_stops': [], 'provider_stops': []}
