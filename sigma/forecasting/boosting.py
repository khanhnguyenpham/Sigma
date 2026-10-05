"""Validate registered booster budgets before any run is written or fitted."""


def estimator_count(spec, settings):
    value = spec.get('n_estimators', settings['n_estimators'])
    if type(value) is not int or not 1 <= value <= 2000:
        raise ValueError('n_estimators must be an integer between 1 and 2000')
    return value


def validate_budgets(settings):
    estimator_count({}, settings)
    for spec in settings['models'].values():
        if 'n_estimators' in spec:
            if not (spec['kind'] == 'lgbm' or
                    (spec['kind'] == 'local_week' and spec.get('estimator') == 'boosted_median')):
                raise ValueError('n_estimators override requires a boosted estimator')
            estimator_count(spec, settings)
