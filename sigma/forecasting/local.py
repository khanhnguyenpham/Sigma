"""Route-specific weekly estimators with causal normalization and missingness."""
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import QuantileRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from sigma.forecasting.linear import features


class WeeklyLocal:
    def __init__(self, spec, cfg, settings):
        self.spec, self.cfg, self.settings = spec, cfg, settings
        self.models = {}

    def inputs(self, x):
        if self.spec['estimator'] == 'annual_median':
            z = features(x, self.spec['harmonics'])
            names = ['prior_year_week7', 'prior_year_mean28_week', 'prior_year_mean90_week']
            z[names] = x[names]
            return z
        if self.spec['estimator'] != 'boosted_median':
            raise ValueError('Unknown local weekly estimator')
        return x.drop(columns='route_index')

    def fit(self, x, y, sample_weight):
        z = self.inputs(x)
        for route in sorted(x.route_index.unique()):
            indices = np.flatnonzero(x.route_index.to_numpy() == route)
            target, weight = y[indices], sample_weight[indices]
            if not np.any(weight > 0):
                model = DummyRegressor(strategy='constant', constant=0.).fit(z.iloc[indices].fillna(0), target)
            else:
                # Each route has its own training weight scale and estimator.
                weight = weight / weight[weight > 0].mean()
                if self.spec['estimator'] == 'annual_median':
                    model = make_pipeline(SimpleImputer(strategy='median', add_indicator=True, keep_empty_features=True),
                        StandardScaler(), QuantileRegressor(quantile=.5, alpha=self.spec['alpha'], solver='highs'))
                    model.fit(z.iloc[indices], target, quantileregressor__sample_weight=weight)
                else:
                    model = LGBMRegressor(objective='regression_l1', num_leaves=self.spec['leaves'],
                        n_estimators=self.settings['n_estimators'], learning_rate=self.settings['learning_rate'],
                        min_child_samples=self.settings['min_child_samples'], reg_lambda=self.settings['reg_lambda'],
                        n_jobs=self.cfg['lightgbm_threads'], random_state=self.cfg['seed'], deterministic=True,
                        force_col_wise=True, verbosity=-1)
                    model.fit(z.iloc[indices], target, sample_weight=weight,
                        categorical_feature=['block', 'origin_weekday', 'start_month'])
            self.models[route] = model
        return self

    def predict(self, x):
        z = self.inputs(x)
        result = np.empty(len(x), dtype=float)
        for route in x.route_index.unique():
            if route not in self.models:
                raise ValueError('No trained local weekly route')
            idx = np.flatnonzero(x.route_index.to_numpy() == route)
            model = self.models[route]
            values = z.iloc[idx].fillna(0) if isinstance(model, DummyRegressor) else z.iloc[idx]
            result[idx] = model.predict(values)
        return result
