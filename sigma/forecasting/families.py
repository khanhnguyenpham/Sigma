"""Compatibility entry point; implementation lives in M2/models."""
import sys
from M2.models import families as implementation

if __name__ == '__main__':
    implementation.main()
else:
    sys.modules[__name__] = implementation
