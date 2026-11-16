"""HTTP routes and the original business columns survive module relocation."""
import json
from pathlib import Path
from main import create_app
from core.settings import Settings
from models import Base
from operations_contract import OPS_TABLES, OPS_ROUTES


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
    for path, methods in OPS_ROUTES.items():
        assert routes.pop(path) == methods
    assert routes.pop('/api/v1/scenarios/{key}') == ['delete']
    assert routes.pop('/api/v1/scenarios/{key}/restore') == ['post']
    assert routes.pop('/api/v1/runs/{key}/retry') == ['post']
    assert routes.pop('/api/v1/runs/{key}/forecasts/origins') == ['get']
    assert routes.pop('/api/v1/runs/{key}/policy-alert-evaluation') == ['get']
    assert routes.pop('/api/v1/runs/{key}/snapshot') == ['get']
    for path, methods in {
        '/api/v1/auth/session': ['get'], '/api/v1/auth/login': ['post'], '/api/v1/auth/logout': ['post'], '/api/v1/auth/password': ['post'],
        '/api/v1/auth/users': ['get', 'post'], '/api/v1/auth/users/{key}': ['patch'],
    }.items():
        assert routes.pop(path) == methods
    # CHG-082 adds product management and a live warehouse read; retain the golden for all existing operations.
    assert routes.pop('/api/v1/products') == ['get']
    assert routes.pop('/api/v1/products/{key}') == ['get']
    assert routes.pop('/api/v1/products/{key}/supply-changes') == ['get', 'post']
    assert routes.pop('/api/v1/products/{key}/internal-stop-preview') == ['post']
    assert routes.pop('/api/v1/products/{key}/receiving-warehouse') == ['patch']
    for path in list(routes):
        if path.startswith('/api/v1/provider-product-notices'):
            routes.pop(path)
    assert routes.pop('/api/v1/runs/{key}/sell-through') == ['get']
    routes['/api/v1/warehouses/{key}'].remove('get')
    # Total30 is removed from the application; historical fixture stays intact.
    assert not any('monthly' in path for path in routes)
    assert routes == {p: methods for p, methods in baseline['routes'].items() if 'monthly' not in p}
    # 0015 renamed supplier_item_policies to item_policies and derived supplier_id from the item carrier.
    renamed = {'supplier_item_policies': 'item_policies'}
    assert set(Base.metadata.tables) == {renamed.get(t, t) for t in baseline['tables']} | {'item_supply_changes',
        'provider_product_notices', 'provider_product_notice_items', 'provider_product_notice_events', 'auth_users', 'auth_sessions', 'run_configs', 'run_results'} | OPS_TABLES
    assert len(Base.metadata.tables) == 33  # 28 + three dealer tables (0012) + run_configs/run_results (0016)
    for name, columns in baseline['tables'].items():
        if name == 'suppliers':
            columns = [c for c in columns if c not in {'code', 'display_name', 'is_assumed', 'assumption_source'}]
            assert set(Base.metadata.tables[name].columns.keys()) == {'id', 'carrier', 'created_at'}
        if name == 'supplier_item_policies':
            columns = [c for c in columns if c != 'supplier_id']
        # 0016: verification hashes dropped; run JSON documents live in run_configs/run_results.
        columns = [c for c in columns if not c.endswith('_sha256')]
        if name == 'runs':
            moved = {'config_snapshot', 'result_summary', 'artifact_manifest'}
            assert moved <= set(Base.metadata.tables['run_configs'].columns.keys()) | set(Base.metadata.tables['run_results'].columns.keys())
            columns = [c for c in columns if c not in moved]
        assert set(columns) <= set(Base.metadata.tables[renamed.get(name, name)].columns.keys())
    app.state.engine.dispose()
