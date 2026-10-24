"""HTTP routes and the original business columns survive module relocation."""
import json
from pathlib import Path
from sigma_m3.main import create_app
from sigma_m3.settings import Settings
from sigma_m3.models import Base


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
    assert routes == baseline['routes']
    assert set(Base.metadata.tables) == set(baseline['tables'])
    assert len(Base.metadata.tables) == 13
    for name, columns in baseline['tables'].items():
        assert set(columns) <= set(Base.metadata.tables[name].columns.keys())
    app.state.engine.dispose()
