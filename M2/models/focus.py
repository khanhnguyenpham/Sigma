"""Fixed LG U+ final: pooled annual ratio, scale56/window540, multiply56/prior4."""
import numpy as np
import pandas as pd
from M2.models.weekly import prepare, checked_series, fit, predict_batch
from M2.models.calibration import relative_factor
from M2.models.common import prediction_rows, COLUMNS, effective_settings

FOCUS = ('South Korea', 'LG U+')

def load_predictions(path):
    return pd.read_csv(path, parse_dates=['as_of_date', 'target_date', 'window_start'], float_precision='round_trip')

def candidates(experiment):
    result = {f'{parent}_{head}': {'parent': parent, **spec}
              for parent in experiment['parents'] for head, spec in experiment['heads'].items()}
    return result

def prepare_parent(daily, settings, changes):
    prepared = prepare(daily, {**settings, 'blocks': [1, 2], 'models': {}})
    for (route, _), table in prepared.items():
        part = daily.loc[daily.destination_country.eq(route[0]) & daily.carrier.eq(route[1])].set_index('date').sort_index()
        y = part.sales_qty
        origin = table['origins']
        scale_days = changes.get('scale_days', 90)
        if scale_days != 90:
            table['scale'] = (y.rolling(scale_days, min_periods=scale_days).mean()*7).clip(lower=1).reindex(origin).to_numpy()
    return prepared

def transform(value, scale, spec, parameters):
    return max(0., value*parameters[0])


def phase(daily, cfg, settings, experiment, split, wanted=None):
    """Fit pooled teachers using only completed labels; emit only the focus route."""
    specifications = candidates(experiment)
    wanted = list(specifications) if wanted is None else list(wanted)
    required = set(wanted)
    parent_names = {specifications[name]['parent'] for name in required}
    groups = {key: part.sales_qty.astype(float) for key, part in checked_series(daily).items()}
    if FOCUS not in groups:
        raise ValueError('Focus absent from train-only population')
    end = pd.Timestamp(cfg[f'{split}_end']) if split != 'future' else daily.date.max()
    origins = pd.date_range(pd.Timestamp(cfg[f'{split}_start'])-pd.Timedelta(days=1), end-pd.Timedelta(days=1)) if split != 'future' else [end]
    frames, logs = [], []
    base = settings['models']['LightGBM']['lgbm_annual_ratio7']
    for parent in experiment['parents']:
        if parent not in parent_names:
            continue
        changes = experiment['parents'][parent]
        prepared = prepare_parent(daily, settings, changes)
        training = prepared  # All train top10 routes remain in the pooled fit.
        spec = {'kind': 'lgbm', 'units': 'ratio', **base, **changes}
        effective = effective_settings(settings, changes)
        fit_cache, prediction_cache = {}, {}
        def teacher(origin):
            if origin not in fit_cache:
                fit_cache[origin] = fit(training, origin, spec, cfg, effective)
                logs.append({'status': 'fit', 'parent': parent, 'fit_cutoff': origin, **fit_cache[origin][1]})
            return fit_cache[origin][0]
        def prediction(origin):
            if origin not in prediction_cache:
                prediction_cache[origin] = predict_batch(teacher(origin), prepared, origin, spec)
            return prediction_cache[origin]
        heads = {name: specifications[name] for name in required
                 if specifications[name]['parent'] == parent}
        parameters = {}
        for i, origin in enumerate(origins):
            if i % settings['refit_days'] == 0:
                model, cutoff = teacher(origin), origin
                for name, head in heads.items():
                    for block in (1, 2):
                        p, y, label_ends = [], [], []
                        table = prepared[(FOCUS, block)]
                        for past in pd.date_range(origin-pd.Timedelta(days=head['history_days']), origin-pd.Timedelta(days=7), freq='7D'):
                            idx = np.flatnonzero(table['origins'] == past)
                            if len(idx) != 1:
                                raise ValueError('Missing teacher origin')
                            idx = idx[0]
                            finish = table['ends'][idx]
                            if finish > origin:
                                continue
                            forecast = prediction(past)[(FOCUS, block)]
                            actual = table['y'][idx]
                            p.append(forecast); y.append(actual); label_ends.append(finish)
                            logs.append({'status': 'head_pair', 'model': name, 'parent': parent, 'week_block': block,
                                'fit_cutoff': origin, 'teacher_origin': past, 'max_label_end': fit_cache[past][1]['max_label_end'],
                                'head_label_end': finish, 'forecast_qty': forecast, 'actual_qty': actual})
                        if not label_ends or max(label_ends) > origin:
                            raise ValueError('Incomplete causal head history')
                        idx = np.flatnonzero(table['origins'] == origin)[0]
                        scale = float(table['scale'][idx])
                        beta = np.array([relative_factor(p, y, head['prior_weeks']), 0.])
                        parameters[(name, block)] = (beta, scale)
                        logs.append({'status': 'head', 'model': name, 'parent': parent, 'week_block': block,
                            'fit_cutoff': origin, 'max_head_label_end': max(label_ends), 'n_weeks': len(y),
                            'beta0': beta[0], 'beta1': beta[1], 'head_scale': scale})
            predicted = predict_batch(model, prepared, origin, spec)
            for name, head in heads.items():
                values = []
                for block in (1, 2):
                    value = predicted[(FOCUS, block)]
                    beta, scale = parameters[(name, block)]
                    corrected = transform(value, scale, head, beta)
                    logs.append({'status': 'applied', 'model': name, 'week_block': block, 'as_of_date': origin,
                        'fit_cutoff': cutoff, 'forecast_qty': value, 'corrected_forecast_qty': corrected,
                        'beta0': beta[0], 'beta1': beta[1], 'head_scale': scale})
                    value = corrected
                    values.append(value)
                frames.extend(prediction_rows(groups[FOCUS], FOCUS, 'FocusResearch', 'direct_7d', name, split, origin, end, values))
        print(f'{split}: {parent} ({len(heads)} outputs)', flush=True)
    result = pd.DataFrame(frames, columns=COLUMNS)
    return result.loc[result.model.isin(wanted)].reset_index(drop=True), pd.DataFrame(logs)

def verify_heads(log, experiment, daily):
    specs = candidates(experiment)
    count = 0
    if log.empty:
        return count
    fits = log.loc[log.status.eq('fit')]
    assert (fits.max_label_end <= fits.fit_cutoff).all()
    actual = daily.loc[daily.destination_country.eq(FOCUS[0]) & daily.carrier.eq(FOCUS[1])].set_index('date').sales_qty.rolling(7).sum()
    for head in log.loc[log.status.eq('head')].itertuples():
        pairs = log.loc[log.status.eq('head_pair') & log.model.eq(head.model)
                        & log.fit_cutoff.eq(head.fit_cutoff) & log.week_block.eq(head.week_block)]
        assert (pairs.max_label_end <= pairs.teacher_origin).all()
        assert (pairs.head_label_end <= pairs.fit_cutoff).all() and len(pairs) == head.n_weeks
        spec = specs[head.model]
        origins = pd.date_range(head.fit_cutoff-pd.Timedelta(days=spec['history_days']), head.fit_cutoff-pd.Timedelta(days=7), freq='7D')
        origins = origins[origins+pd.Timedelta(days=7*int(head.week_block)) <= head.fit_cutoff]
        assert pd.DatetimeIndex(pairs.teacher_origin).equals(origins)
        assert (pairs.head_label_end == pairs.teacher_origin+pd.to_timedelta(7*pairs.week_block,unit='D')).all()
        np.testing.assert_array_equal(pairs.actual_qty,actual.reindex(pairs.head_label_end))
        beta = np.array([relative_factor(pairs.forecast_qty, pairs.actual_qty, spec['prior_weeks']), 0.])
        np.testing.assert_allclose(beta, [head.beta0, head.beta1], atol=1e-8, rtol=0)
        applied = log.loc[log.status.eq('applied') & log.model.eq(head.model)
                          & log.fit_cutoff.eq(head.fit_cutoff) & log.week_block.eq(head.week_block)]
        expected = [transform(v, head.head_scale, spec, beta) for v in applied.forecast_qty]
        np.testing.assert_allclose(expected, applied.corrected_forecast_qty, atol=1e-8, rtol=0)
        count += 1
    return count
