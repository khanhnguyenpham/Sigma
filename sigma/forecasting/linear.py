"""Per-route regularized median regressions for smooth weekly seasonality."""
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import QuantileRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def features(x, harmonics):
    result = x[['block', 'year_sin', 'year_cos', 'elapsed_days', 'sum28', 'previous7']].copy()
    if harmonics == 2:
        result['year_sin2'] = 2 * x.year_sin * x.year_cos
        result['year_cos2'] = x.year_cos ** 2 - x.year_sin ** 2
    elif harmonics != 1:
        raise ValueError('Weekly linear harmonics must be one or two')
    if not np.isfinite(result.to_numpy()).all():
        raise ValueError('Missing weekly linear history')
    return result


class WeeklyLinear:
    def __init__(self, spec):
        self.spec = spec
        self.models = {}

    def fit(self, x, y, sample_weight):
        if self.spec['alpha'] < 0:
            raise ValueError('Negative weekly linear regularization')
        z = features(x, self.spec['harmonics'])
        for route in sorted(x.route_index.unique()):
            indices = np.flatnonzero(x.route_index.to_numpy() == route)
            target, weight = y[indices], sample_weight[indices]
            if not np.any(weight > 0):
                model = DummyRegressor(strategy='constant', constant=0.).fit(z.iloc[indices], target)
            else:
                model = make_pipeline(StandardScaler(), QuantileRegressor(
                    quantile=.5, alpha=self.spec['alpha'], solver='highs'))
                # Normalize only training weights; this fixes the alpha scale.
                weight = weight / weight[weight > 0].mean()
                model.fit(z.iloc[indices], target, quantileregressor__sample_weight=weight)
            self.models[route] = model
        return self

    def predict(self, x):
        z = features(x, self.spec['harmonics'])
        result = np.empty(len(x), dtype=float)
        for route in x.route_index.unique():
            if route not in self.models:
                raise ValueError('No trained weekly linear route')
            idx = np.flatnonzero(x.route_index.to_numpy() == route)
            result[idx] = self.models[route].predict(z.iloc[idx])
        return result
