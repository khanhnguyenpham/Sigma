"""Hash implementation files, including imported core code, rather than aliases."""
from src.common import ROOT, sha256


def implementation_hashes(*packages):
    paths = {ROOT / 'sigma' / '__init__.py', ROOT / 'sigma' / 'provenance.py'}
    paths.update((ROOT / 'src').glob('*.py'))
    for package in packages:
        folder = (ROOT / 'sigma' / package).resolve()
        if not folder.is_relative_to((ROOT / 'sigma').resolve()) or not folder.is_dir():
            raise ValueError('Invalid implementation package')
        paths.update(folder.rglob('*.py'))
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in sorted(paths)}
