"""Legacy imports share actual globals, and provenance detects implementation edits."""
import legacy.weekly_forecast as weekly_forecast
import legacy.weekly_inventory as weekly_inventory
import sigma.forecasting.weekly as weekly
import sigma.inventory.snapshot as stock
from sigma.provenance import implementation_hashes


def test_legacy_alias_is_the_implementation_module_for_monkeypatching():
    assert weekly_forecast is weekly
    assert weekly_inventory is stock
    assert weekly_forecast.fit.__module__ == 'sigma.forecasting.weekly'


def test_provenance_hashes_real_models_and_core_instead_of_only_aliases():
    files = implementation_hashes('forecasting')
    assert 'sigma/forecasting/weekly.py' in files and 'sigma/forecasting/calibration.py' in files
    assert 'src/data.py' in files and 'sigma/provenance.py' in files
    assert 'weekly_forecast.py' not in files
