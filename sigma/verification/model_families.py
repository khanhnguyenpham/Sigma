"""Compatibility entry point for the M2 independent verifier."""
import runpy
import sys
from M2.models import verify as implementation

if __name__ == '__main__':
    runpy.run_module('M2.models.verify', run_name='__main__')
else:
    sys.modules[__name__] = implementation
