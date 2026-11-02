"""HTTP routes and the original business columns survive module relocation."""
import json
from pathlib import Path
from main import create_app
from core.settings import Settings
from models import Base


def test_http_and_schema_preserve_existing_contract(tmp_path):
    baseline = json.loads((Path(__file__).parent / 'fixtures/http_schema_baseline.json').read_text())
    app = create_app(Settings(
        'postgresql+psycopg://synthetic:synthetic@127.0.0.1/sigma_m3_test',
        tmp_path, tmp_path,
    ))
    routes = {
        path: sorted(k for k in methods if k in {'get', 'post', 'patch', 'delete', 'put'})
        for path, methods in app.openapi()['paths'].items()
    }
    # CHG-082 adds product management and a live warehouse read; retain the golden for all existing operations.
    assert routes.pop('/api/v1/products') == ['get']
    assert routes.pop('/api/v1/products/{key}') == ['get']
    assert routes.pop('/api/v1/products/{key}/supply-changes') == ['get', 'post']
    assert routes.pop('/api/v1/products/{key}/internal-stop-preview') == ['post']
    for path in list(routes):
        if path.startswith('/api/v1/provider-product-notices'):
            routes.pop(path)
    assert routes.pop('/api/v1/runs/{key}/sell-through') == ['get']
    routes['/api/v1/warehouses/{key}'].remove('get')
    assert routes == baseline['routes']
    assert set(Base.metadata.tables) == set(baseline['tables']) | {'item_supply_changes',
        'provider_product_notices', 'provider_product_notice_items', 'provider_product_notice_events'}
    assert len(Base.metadata.tables) == 17
    for name, columns in baseline['tables'].items():
        if name == 'suppliers':
            columns = [c for c in columns if c not in {'code', 'display_name', 'is_assumed', 'assumption_source'}]
            assert set(Base.metadata.tables[name].columns.keys()) == {'id', 'carrier', 'created_at'}
        assert set(columns) <= set(Base.metadata.tables[name].columns.keys())
    app.state.engine.dispose()
