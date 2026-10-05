import pandas as pd
import pytest

import verify_release
from src.common import sha256, seal_manifest, write_csv
from src.evaluation import metric_table


@pytest.mark.parametrize('tamper', ['actual_quantity', 'validation_metric', 'missing_forecast'])
def test_independent_validation_verifier_rejects_wrong_target_or_metric(tmp_path, monkeypatch, tamper):
    # Disposable synthetic evidence: source truth is two units, not one order.
    source = tmp_path/'fake_source.txt'; source.write_text('synthetic source only')
    daily = pd.DataFrame({'date': pd.to_datetime(['2024-01-02']), 'destination_country': ['Synthetic'],
                          'carrier': ['fake'], 'sales_qty': [2.]})
    top = daily[['destination_country', 'carrier']].assign(train_quantity=2., rank=1)
    predictions = pd.DataFrame({'as_of_date': pd.to_datetime(['2024-01-01']), 'target_date': pd.to_datetime(['2024-01-02']),
        'destination_country': ['Synthetic'], 'carrier': ['fake'], 'model': ['ma7'], 'horizon_day': [1],
        'forecast_qty': [3.], 'actual_qty': [2.], 'split': ['validation']})
    metrics = metric_table(predictions)
    if tamper == 'actual_quantity': predictions['actual_qty'] = 1.
    elif tamper == 'validation_metric': metrics['mae'] = 0.
    else: predictions['forecast_qty'] = float('nan')
    folder = tmp_path/'run'; folder.mkdir()
    for name, frame in [('daily_sales.csv', daily), ('top_routes.csv', top),
                        ('selected_models.csv', top.assign(model='ma7')),
                        ('baseline_validation_predictions.csv', predictions), ('validation_metrics.csv', metrics)]:
        write_csv(folder/name, frame)
    seal_manifest(folder, {'status': 'complete', 'config': {'source': source.name, 'validation_end': '2024-01-02', 'numeric_tolerance': 1e-8},
                          'source_sha256': sha256(source), 'code_sha256': 'synthetic'})
    monkeypatch.setattr(verify_release, 'ROOT', tmp_path)
    monkeypatch.setattr(verify_release, 'code_hash', lambda: 'synthetic')
    monkeypatch.setattr(verify_release, 'audit_orders', lambda *args: (pd.DataFrame(), {}))
    monkeypatch.setattr(verify_release, 'daily_sales', lambda *args: daily)
    monkeypatch.setattr(verify_release, 'route_top', lambda *args: top)
    message = {'actual_quantity': 'Validation actual quantities',
               'validation_metric': 'Validation metrics differ',
               'missing_forecast': 'Missing validation forecast without a logged'}[tamper]
    with pytest.raises(ValueError, match=message): verify_release.verify(folder)
