"""Compatibility entry point; implementation: sigma.verification.data_check."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    import runpy
    runpy.run_module('sigma.verification.data_check', run_name='__main__')
else:
    import importlib
    sys.modules[__name__] = importlib.import_module('sigma.verification.data_check')
