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


def opportunity_breakdown(cases):
    """Post-replay explanation only; never an input to forecasts or policy."""
    histogram = {day: dict(lead_days=day, events=0, detected=0) for day in range(1, 15)}
    excluded = 0
    for case in cases:
        if not case["is_evaluable"]:
            excluded += 1
            continue
        origin = case["as_of_date"]
        predicted = case["predicted_depletion_date"]
        actual = case["actual_depletion_date"]
        if predicted is not None and not 1 <= (predicted - origin).days <= 14:
            raise ValueError("Replay prediction outside its 14-day window")
        if actual is None:
            continue
        lead = (actual - origin).days
        if lead not in histogram:
            raise ValueError("Replay event outside its 14-day window")
        histogram[lead]["events"] += 1
        histogram[lead]["detected"] += int(predicted is not None)
    early_possible = sum(r["events"] for d, r in histogram.items() if d >= 7)
    early_detected = sum(r["detected"] for d, r in histogram.items() if d >= 7)
    short = sum(r["events"] for d, r in histogram.items() if d < 7)
    denominator = short + early_possible
    return dict(
        scope="whole_alert_replay",
        basis="posthoc_actual_event_timing_not_a_forecast",
        event_denominator=denominator,
        excluded_count=excluded,
        observed_early_numerator=early_detected,
        short_notice_events=short,
        eligible_early_events=early_possible,
        missed_eligible_events=early_possible - early_detected,
        observed_early_rate=early_detected / denominator if denominator else None,
        theoretical_max_early_rate=early_possible / denominator
        if denominator
        else None,
        eligible_detection_rate=early_detected / early_possible
        if early_possible
        else None,
        histogram=list(histogram.values()),
    )
