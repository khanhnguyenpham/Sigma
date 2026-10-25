import pandas as pd
import pytest
from modules.forecasting.service import select_new
from modules.forecasting import m2_adapter
from core.errors import DomainError


def fixture():
    cfg = {
        "validation_start": "2025-07-01",
        "validation_end": "2025-07-31",
        "mape_limit_pct": 20,
    }
    records = []
    for model, value in [("a", 11), ("b", 12)]:
        for origin in pd.date_range("2025-06-30", "2025-07-30"):
            for block in (1, 2):
                records.append(
                    dict(
                        family="LightGBM",
                        model=model,
                        target="direct_7d",
                        split="validation",
                        destination_country="Demo",
                        carrier="DemoNet",
                        as_of_date=origin,
                        block=block,
                        target_date=origin + pd.Timedelta(days=7 * block),
                        forecast_qty=float(value),
                        actual_qty=10.0,
                    )
                )
    return pd.DataFrame(records), cfg


def test_selection_uses_validation_and_rejects_missing_candidate_pairs():
    frame, cfg = fixture()
    routes = [("Demo", "DemoNet")]
    pool = [("LightGBM", "a"), ("LightGBM", "b")]
    selected, _ = select_new(frame, cfg, routes, pool)
    assert selected[0]["model"] == "a"
    selected, _ = select_new(frame.drop(frame.index[0]), cfg, routes, pool)
    assert selected[0]["model"] == "b"
    with pytest.raises(DomainError):
        select_new(frame.assign(split="test"), cfg, routes, pool)


def test_zero_positive_mape_uses_mae_then_model_id():
    frame, cfg = fixture()
    frame.actual_qty = 0
    frame.forecast_qty = 2
    selected, _ = select_new(
        frame, cfg, [("Demo", "DemoNet")], [("LightGBM", "b"), ("LightGBM", "a")]
    )
    assert (
        selected[0]["model"] == "a"
        and selected[0]["validation_mape_positive_pct"] is None
    )


def test_top10_adapter_never_sends_other_routes_to_fixed_pool(monkeypatch):
    records = []
    for name in ["Fixed", "New"]:
        for day in pd.date_range("2024-01-01", periods=4):
            records.append(
                dict(
                    destination_country="Demo",
                    carrier=name,
                    date=day,
                    sales_qty=1,
                    order_count=1,
                )
            )
    data = pd.DataFrame(records)
    captured = []
    monkeypatch.setattr(
        m2_adapter,
        "configuration",
        lambda: (
            {},
            {},
            {
                "routes": [
                    dict(destination_country="Demo", carrier="Fixed", model="fixed")
                ]
            },
        ),
    )

    def replay(frame, *args):
        captured.append(set(frame.carrier))
        return pd.DataFrame(
            [dict(destination_country="Demo", carrier="Fixed", model="fixed")]
        ), {}

    monkeypatch.setattr(m2_adapter, "final_replay", replay)
    m2_adapter.top10(data, "test")
    assert captured == [{"Fixed"}]
