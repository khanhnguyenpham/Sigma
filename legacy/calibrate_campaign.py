"""Compatibility entry point; implementation: sigma.experiments.calibration."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == '__main__':
    import runpy
    runpy.run_module('sigma.experiments.calibration', run_name='__main__')
else:
    import importlib
    import sys
    sys.modules[__name__] = importlib.import_module('sigma.experiments.calibration')
