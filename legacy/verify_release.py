"""Compatibility entry point; implementation: sigma.verification.daily_release."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    import runpy
    runpy.run_module('sigma.verification.daily_release', run_name='__main__')
else:
    import importlib
    sys.modules[__name__] = importlib.import_module('sigma.verification.daily_release')
