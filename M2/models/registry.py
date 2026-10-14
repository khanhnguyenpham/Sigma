"""Explicit model registration and each family's variant configuration."""
import json
from src.common import ROOT, sha256
from M2.models.LightGBM import model as lightgbm
from M2.models.Prophet import model as prophet
from M2.models.common import TARGETS, active_variants

REGISTRY = {'LightGBM': lightgbm, 'Prophet': prophet}


def load_settings(path):
    settings = json.loads(path.read_text(encoding='utf-8'))
    for name, variants in list(settings['models'].items()):
        if name not in REGISTRY:
            raise ValueError(f'Unregistered model family: {name}')
        if isinstance(variants, str):
            variant_path = (ROOT/variants).resolve()
            if not variant_path.is_relative_to(ROOT/'M2/models'):
                raise ValueError('Variant configuration must be inside M2/models')
            variants = json.loads(variant_path.read_text(encoding='utf-8'))
        if not isinstance(variants, dict) or not variants or not all(isinstance(spec,dict) for spec in variants.values()):
            raise ValueError('A model family needs named variant specifications')
        settings['models'][name] = variants
        for spec in variants.values():
            targets = spec.get('targets', TARGETS)
            if not targets or not set(targets).issubset(TARGETS):
                raise ValueError('Unknown or empty variant targets')
            for key in ('training_window_days', 'n_estimators', 'min_child_samples'):
                if key in spec and (type(spec[key]) is not int or spec[key] < 1):
                    raise ValueError(f'{key} must be a positive integer')
            if spec.get('units', 'raw') not in ('raw', 'ratio'):
                raise ValueError('Unknown variant units')
        for target in TARGETS:
            if not active_variants(settings, name, target):
                raise ValueError('Each family needs a direct_7d variant')
    if not 1 <= settings.get('workers', 1) <= 3:
        raise ValueError('M2 uses at most three workers')
    return settings


def implementation_hashes():
    paths = [p for p in (ROOT/'M2/models').rglob('*.py') if 'tests' not in p.parts]
    paths += list((ROOT/'src').glob('*.py'))
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted(paths)}
