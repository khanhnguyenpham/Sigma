"""Compatibility entry point; implementation: sigma.ui.product."""
if __name__ == '__main__':
    import runpy
    runpy.run_module('sigma.ui.product', run_name='__main__')
else:
    import importlib
    import sys
    sys.modules[__name__] = importlib.import_module('sigma.ui.product')
