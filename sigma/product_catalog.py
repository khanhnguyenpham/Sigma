"""A frozen presentation bundle never silently switches to newer artifacts."""
import re

from src.common import ROOT, sha256


def candidate_folders(bundle, role):
    pinned = bundle.get('product_runs')
    if pinned is None:
        return sorted((ROOT / 'outputs').glob('*'))
    if role not in pinned:
        raise ValueError('Frozen product bundle has no ' + role)
    ident = pinned[role]
    if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
        raise ValueError('Invalid frozen product run id')
    folder = ROOT / 'outputs' / ident
    name = 'manifest.json' if role == 'daily' else 'summary.json'
    expected = bundle.get('product_summary_hashes', {}).get(role)
    if not expected or sha256(folder / name) != expected:
        raise ValueError('Frozen product artifact missing or changed: ' + role)
    return [folder]
