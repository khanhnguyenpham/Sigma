"""Public calendar reference, origin-aware features and train-only peak analysis."""
import json
from functools import lru_cache

import holidays
import numpy as np
import pandas as pd

from src.common import ROUTE, write_csv, write_json
from src.data import observed_anomalies

CODES = {'Thailand': 'TH', 'Japan': 'JP', 'South Korea': 'KR', 'China': 'CN'}
HOLIDAY_FIELDS = ['holiday', 'before7', 'after7', 'days_to', 'days_since']
SEASON_FIELDS = ['summer_hypothesis', 'spring_hypothesis', 'autumn_hypothesis']
GROUPS = ('none', 'vn', 'destination', 'both', 'both_season')


def feature_names(group):
    if group not in GROUPS:
        raise ValueError('Unknown calendar feature group')
    prefixes = ([] if group == 'none' else ['vn'] if group == 'vn' else
                ['destination'] if group == 'destination' else ['vn', 'destination'])
    names = [f'cal_{prefix}_{field}' for prefix in prefixes for field in HOLIDAY_FIELDS]
    return names + ([f'cal_{field}' for field in SEASON_FIELDS] if group == 'both_season' else [])


def event_catalog(settings):
    """Keep missing announcement dates explicit; never backdate special holidays."""
    low = pd.Timestamp(settings['calendar_start']) - pd.Timedelta(days=settings['buffer_days'])
    high = pd.Timestamp(settings['calendar_end']) + pd.Timedelta(days=settings['buffer_days'])
    overrides = {(r['country_code'], r['date']): r for r in settings['overrides']}
    events = []
    for code in ['VN', *CODES.values()]:
        calendar = holidays.country_holidays(code, years=range(low.year, high.year + 1), language='en_US')
        for date, name in sorted(calendar.items()):
            day = pd.Timestamp(date)
            if not low <= day <= high:
                continue
            annual = settings['annual_sources'].get(code, {}).get(str(day.year))
            special = any(word in name.lower() for word in ('bridge', 'temporary', 'day off', 'armed forces', 'presidential election'))
            metadata = {'known_from': settings['recurring_rule_known_from'],
                        'source': settings['country_sources'].get(code, 'https://github.com/vacanza/holidays'),
                        'verification_status': settings['recurring_rule_status']}
            if annual:
                metadata.update(annual, verification_status='annual_schedule_source_checked')
            if special and not annual:
                metadata.update(known_from=None, verification_status='unverified_announcement_excluded')
            override = overrides.get((code, str(date)))
            if override:
                metadata.update({k: override[k] for k in ('known_from', 'source')},
                                verification_status='dated_official_source_checked')
            events.append({'country_code': code, 'date': str(date), 'name': name,
                           'kind': 'library_public_holiday',
                           'is_observed': any(word in name.lower() for word in ('observed', 'alternative', 'substitute', 'in lieu', 'day off')),
                           **metadata})
    for period in settings['breaks']:
        for day in pd.date_range(period['start'], period['end']):
            if low <= day <= high:
                events.append({'country_code': period['country_code'], 'date': str(day.date()),
                               'name': period['name'], 'kind': 'public_office_break', 'is_observed': False,
                               'known_from': period['known_from'], 'source': period['source'],
                               'verification_status': 'dated_official_source_checked'})
    return sorted(events, key=lambda r: (r['country_code'], r['date'], r['kind'], r['name']))


def holiday_view(days, events):
    """Union consecutive holiday days into periods without multiplying daily rows."""
    days = pd.DatetimeIndex(days)
    frame = pd.DataFrame(index=days)
    by_day = {}
    for event in events:
        by_day.setdefault(pd.Timestamp(event['date']), []).append(event)
    dates = pd.DatetimeIndex(sorted(by_day))
    frame['holiday'] = days.isin(dates).astype(int)
    frame['holiday_name'] = ['; '.join(dict.fromkeys(e['name'] for e in by_day.get(day, []))) for day in days]
    frame['is_observed'] = [int(any(e['is_observed'] for e in by_day.get(day, []))) for day in days]
    frame['is_public_office_break'] = [int(any(e['kind'] == 'public_office_break' for e in by_day.get(day, []))) for day in days]
    frame['period_start'], frame['period_end'] = pd.NaT, pd.NaT
    frame['related_period_start'], frame['related_period_end'] = pd.NaT, pd.NaT
    frame['related_holiday_name'], frame['related_source'] = '', ''
    closest = np.full(len(days), 15)
    frame['days_to'], frame['days_since'] = 15, 15  # clipped distances, 15 means outside 14 days
    if len(dates):
        groups = pd.Series(dates, index=dates).groupby(pd.Series(dates).diff().dt.days.ne(1).cumsum().to_numpy())
        for _, period in groups:
            start, end = period.min(), period.max()
            within = (days >= start) & (days <= end)
            frame.loc[within, ['period_start', 'period_end']] = [start, end]
            to = np.where(days < start, (start - days).days, np.where(within, 0, 15))
            since = np.where(days > end, (days - end).days, np.where(within, 0, 15))
            frame['days_to'] = np.minimum(frame.days_to, np.clip(to, 0, 15))
            frame['days_since'] = np.minimum(frame.days_since, np.clip(since, 0, 15))
            distance = np.where(within, 0, np.minimum(np.abs((start-days).days), np.abs((end-days).days)))
            nearby = (distance <= 14) & (distance < closest)
            closest = np.minimum(closest, distance)
            period_events = [e for date in period for e in by_day[date]]
            frame.loc[nearby, ['related_period_start', 'related_period_end']] = [start, end]
            frame.loc[nearby, 'related_holiday_name'] = '; '.join(dict.fromkeys(e['name'] for e in period_events))
            frame.loc[nearby, 'related_source'] = '; '.join(dict.fromkeys(e['source'] for e in period_events))
    frame['before7'] = frame.days_to.between(1, 7).astype(int)
    frame['after7'] = frame.days_since.between(1, 7).astype(int)
    for field in ['source', 'known_from', 'verification_status']:
        frame[field] = ['; '.join(dict.fromkeys(str(e[field]) if e[field] is not None else 'unknown'
                                             for e in by_day.get(day, []))) for day in days]
    return frame


def seasons(days, country):
    months = pd.DatetimeIndex(days).month
    return pd.DataFrame({'summer_hypothesis': ((months >= 6) & (months <= 8)).astype(int),
        'spring_hypothesis': (np.isin(months, [3, 4, 5]) & (country in ('Japan', 'South Korea'))).astype(int),
        'autumn_hypothesis': (np.isin(months, [9, 10, 11]) & (country in ('Japan', 'South Korea'))).astype(int)},
        index=pd.DatetimeIndex(days))


def build_reference(settings):
    days = pd.date_range(settings['calendar_start'], settings['calendar_end'])
    events = event_catalog(settings)
    views = {code: holiday_view(days, [e for e in events if e['country_code'] == code])
             for code in ['VN', *CODES.values()]}
    frames = []
    for country, code in sorted(CODES.items()):
        frame = pd.DataFrame({'date': days, 'destination_country': country, 'country_code': code,
            'year': days.year, 'weekday': days.dayofweek, 'iso_week': days.isocalendar().week.to_numpy(),
            'month': days.month, 'quarter': days.quarter, 'day_of_year': days.dayofyear,
            'is_weekend': (days.dayofweek >= 5).astype(int)})
        for prefix, calendar in [('vn', views['VN']), ('destination', views[code])]:
            for name in calendar:
                frame[f'{prefix}_{name}'] = calendar[name].to_numpy()
        for name, values in seasons(days, country).items():
            frame[name] = values.to_numpy()
        frame['season_status'] = 'user_approved_broad_hypothesis_not_observed_tourist_demand'
        frame['season_source'] = settings['season_sources']['summer'] + '; ' + settings['season_sources'].get(country, '')
        frame['access_date'] = settings['access_date']
        frame['calendar_snapshot_note'] = 'Reference includes later announcements; model must rebuild holiday flags as of each origin'
        frames.append(frame)
    return pd.concat(frames, ignore_index=True), events


class CalendarReference:
    def __init__(self, frame, events):
        self.frame = frame.copy()
        self.frame['date'] = pd.to_datetime(self.frame.date)
        if self.frame.duplicated(['destination_country', 'date']).any():
            raise ValueError('Duplicate calendar dates')
        self.events = events
        self.days = pd.DatetimeIndex(sorted(self.frame.date.unique()))
        if not self.days.equals(pd.date_range(self.days.min(), self.days.max())):
            raise ValueError('Calendar has missing days')
        for country, group in self.frame.groupby('destination_country'):
            if not pd.DatetimeIndex(group.date).sort_values().equals(self.days):
                raise ValueError('Incomplete country calendar')
            expected = seasons(group.date, country).to_numpy()
            if not np.array_equal(group[SEASON_FIELDS].to_numpy(), expected):
                raise ValueError('Calendar season fields differ from registered hypotheses')

    @classmethod
    def load(cls, csv_path):
        return cls(pd.read_csv(csv_path), json.loads(csv_path.with_suffix('.events.json').read_text(encoding='utf-8')))

    @lru_cache(maxsize=128)
    def view(self, code, available_indices):
        selected = [self.events[i] for i in available_indices]
        return holiday_view(self.days, selected)

    def as_of(self, country, origin):
        if country not in CODES:
            raise ValueError('Destination calendar unavailable')
        origin = pd.Timestamp(origin)
        frame = self.frame.loc[self.frame.destination_country.eq(country)].set_index('date')[SEASON_FIELDS].copy()
        for prefix, code in [('vn', 'VN'), ('destination', CODES[country])]:
            indices = tuple(i for i, event in enumerate(self.events)
                if event['country_code'] == code and event['known_from'] is not None
                and pd.Timestamp(event['known_from']) <= origin)
            view = self.view(code, indices)
            for field in HOLIDAY_FIELDS:
                frame[f'{prefix}_{field}'] = view[field]
        return frame

    def weekly(self, country, origins, starts):
        rows = []
        for origin, start in zip(origins, starts, strict=True):
            days = pd.date_range(start, periods=7)
            if not days.isin(self.days).all():
                # Training preparation includes unscored tail origins; future labels stay missing.
                rows.append({name: np.nan for name in feature_names('both_season')})
                continue
            window = self.as_of(country, origin).loc[days]
            row = {}
            for prefix in ('vn', 'destination'):
                for field in HOLIDAY_FIELDS:
                    values = window[f'{prefix}_{field}']
                    row[f'cal_{prefix}_{field}'] = values.min() if field in ('days_to', 'days_since') else values.sum()
            row.update({f'cal_{field}': window[field].sum() for field in SEASON_FIELDS})
            rows.append(row)
        return pd.DataFrame(rows)


def attach_features(prepared, reference):
    cache = {}
    for (route, block), table in prepared.items():
        key = (route[0], block)
        if key not in cache:
            cache[key] = reference.weekly(route[0], table['origins'], table['starts'])
        table['x'][feature_names('both_season')] = cache[key].to_numpy()
    return prepared


def analyze_train(daily, cfg, reference):
    train = daily.loc[daily.date.le(pd.Timestamp(cfg['train_end']))].copy()
    anomalies = observed_anomalies(train, cfg)
    flags = anomalies.loc[anomalies.indicator.eq('sales_qty') & anomalies.kind.eq('surge')]
    flags = flags.set_index(ROUTE + ['date'])
    rows = []
    for route, part in train.groupby(ROUTE):
        part = part.sort_values('date').set_index('date')
        y, orders = part.sales_qty, part.order_count
        same_weekday = pd.concat([y.shift(7 * k) for k in range(1, 9)], axis=1).median(axis=1)
        totals = y.rolling(7, min_periods=7).sum()
        prior = pd.concat([totals.shift(7 * k) for k in range(1, 9)], axis=1)
        median = prior.median(axis=1).where(prior.notna().all(axis=1))
        mad = prior.sub(median, axis=0).abs().median(axis=1)
        relative = (totals - median) / median.replace(0, np.nan)
        z = (totals - median) / (1.4826 * mad).clip(lower=1)
        weekly_surge = median.notna() & (totals > median) & (relative.ge(.5) | z.ge(4))
        for day in part.index:
            daily_key = (*route, day)
            for width in (1, 7):
                if width == 1 and daily_key not in flags.index:
                    continue
                if width == 7 and not weekly_surge.loc[day]:
                    continue
                start = day - pd.Timedelta(days=width - 1)
                baseline = float(flags.loc[daily_key, 'past_median']) if width == 1 else median.loc[day]
                value = y.loc[day] if width == 1 else totals.loc[day]
                calendar = reference.frame.loc[reference.frame.destination_country.eq(route[0])
                    & reference.frame.date.between(start, day)]
                descriptions = []
                for prefix in ('vn', 'destination'):
                    for field in ('holiday', 'before7', 'after7'):
                        if calendar[f'{prefix}_{field}'].any():
                            descriptions.append(f'{prefix}_{field}')
                if calendar[SEASON_FIELDS].to_numpy().any():
                    descriptions.append('broad_season_hypothesis')
                rows.append({**dict(zip(ROUTE, route)), 'date': day, 'window_start': start, 'window_days': width,
                    'sales_qty': value, 'order_count': orders.loc[start:day].sum(), 'past_median': baseline,
                    'increase_qty': value - baseline, 'increase_pct': 100 * (value - baseline) / baseline if baseline else np.nan,
                    'same_weekday_prior8_median': same_weekday.loc[day] if width == 1 else np.nan,
                    'method': 'past28_z4_or_increase50pct' if width == 1 else 'prior8_nonoverlapping_weeks_z4_or_increase50pct',
                    'calendar_overlap': '; '.join(descriptions) or 'unexplained_by_registered_calendar',
                    'vn_holiday_names': '; '.join(dict.fromkeys(calendar.vn_related_holiday_name.dropna().loc[lambda s: s.ne('')])),
                    'destination_holiday_names': '; '.join(dict.fromkeys(calendar.destination_related_holiday_name.dropna().loc[lambda s: s.ne('')])),
                    'sources': '; '.join(dict.fromkeys([*calendar.vn_related_source.dropna().loc[lambda s: s.ne('')],
                                                     *calendar.destination_related_source.dropna().loc[lambda s: s.ne('')]])),
                    'interpretation': 'Train-only descriptive coincidence, not causal; never a model feature'})
    peaks = pd.DataFrame(rows)
    details = train.merge(reference.frame, on=['date', 'destination_country'], validate='many_to_one')
    details['surge_day'] = pd.MultiIndex.from_frame(details[ROUTE + ['date']]).isin(flags.index)
    conditions = {'vn_holiday': details.vn_holiday.eq(1), 'destination_holiday': details.destination_holiday.eq(1),
                  'before_or_after': details[['vn_before7', 'vn_after7', 'destination_before7', 'destination_after7']].any(axis=1),
                  'season_hypothesis': details[SEASON_FIELDS].any(axis=1)}
    conditions['ordinary_calendar'] = ~pd.DataFrame(conditions).any(axis=1)
    summaries = []
    for label, mask in conditions.items():
        for route, part in details.loc[mask].groupby(ROUTE):
            summaries.append({**dict(zip(ROUTE, route)), 'calendar_group': label, 'days': len(part),
                'quantity': part.sales_qty.sum(), 'mean_qty': part.sales_qty.mean(), 'median_qty': part.sales_qty.median(),
                'surge_days': int(part.surge_day.sum()), 'non_surge_days': int((~part.surge_day).sum()),
                'interpretation': 'Overlapping descriptive groups; weekday/season/trend may confound'})
    # Same weekday and +/-56-day controls reduce obvious weekday/local-trend confounding.
    matched = []
    event_mask = details.vn_holiday.eq(1) | details.destination_holiday.eq(1)
    for route, part in details.groupby(ROUTE):
        ordinary = part.loc[~event_mask.loc[part.index]]
        for row in part.loc[event_mask.loc[part.index]].itertuples():
            controls = ordinary.loc[ordinary.weekday.eq(row.weekday) & ordinary.date.sub(row.date).abs().le(pd.Timedelta(days=56))]
            matched.append({**dict(zip(ROUTE, route)), 'date': row.date, 'sales_qty': row.sales_qty,
                'matched_weekday_controls': len(controls), 'control_mean_qty': controls.sales_qty.mean(),
                'difference_qty': row.sales_qty - controls.sales_qty.mean(),
                'interpretation': 'Train-only retrospective association; controls can follow event inside train'})
    return peaks, pd.DataFrame(summaries), pd.DataFrame(matched)
