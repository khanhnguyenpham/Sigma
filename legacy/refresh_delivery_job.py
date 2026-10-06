"""Compatibility entry point; implementation: sigma.jobs.refresh."""
if __name__ == '__main__':
    import runpy
    runpy.run_module('sigma.jobs.refresh', run_name='__main__')
else:
    import importlib
    import sys
    sys.modules[__name__] = importlib.import_module('sigma.jobs.refresh')
