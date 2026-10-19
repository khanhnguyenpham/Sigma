from datetime import timedelta
from sigma_m3.services.inventory import quantity, vector14


def project(origin, on_hand, forecast, receipts):
    f = vector14(forecast)
    stock = float(quantity(on_hand))
    lots = {day: quantity(q) for day, q in receipts.items()}
    rows, depletion = [], None
    for h, demand in enumerate(f, 1):
        day = origin + timedelta(days=h)
        stock = max(0.0, stock + lots.get(day, 0) - float(demand))
        rows.append(
            dict(
                date=day.isoformat(),
                closing_forecast=stock,
                receipts_qty=lots.get(day, 0),
            )
        )
        if depletion is None and stock == 0:
            depletion = day
    if on_hand == 0:
        state, depletion, lead = "already_depleted", origin, 0
    else:
        lead = (depletion - origin).days if depletion else None
        state = (
            "not_within_horizon" if lead is None else "early" if lead >= 7 else "urgent"
        )
    return dict(
        state=state, predicted_depletion_date=depletion, lead_days=lead, projection=rows
    )


def replay_metrics(cases):
    """One row per item/window, including no-alert/no-event and excluded rows."""
    counts = dict(TP=0, FP=0, FN=0, TN=0)
    early = total = excluded = late = 0
    errors = []
    for row in cases:
        if row.get("already_depleted") or not row.get("is_evaluable", True):
            excluded += 1
            continue
        predicted, actual = (
            row.get("predicted_depletion_date"),
            row.get("actual_depletion_date"),
        )
        counts[
            "TP"
            if predicted and actual
            else "FP"
            if predicted
            else "FN"
            if actual
            else "TN"
        ] += 1
        if actual:
            total += 1
            is_early = predicted is not None and (actual - row["as_of_date"]).days >= 7
            early += int(is_early)
            late += int(predicted is not None and not is_early)
        if predicted and actual:
            errors.append(abs((predicted - actual).days))

    def ratio(n, d):
        return n / d if d else None

    return dict(
        **counts,
        precision=ratio(counts["TP"], counts["TP"] + counts["FP"]),
        recall=ratio(counts["TP"], counts["TP"] + counts["FN"]),
        early_numerator=early,
        event_denominator=total,
        early_rate=ratio(early, total),
        late_count=late,
        date_mae=sum(errors) / len(errors) if errors else None,
        excluded_count=excluded,
    )
