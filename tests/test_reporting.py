import pandas as pd
from src.reporting import eda


def test_unknown_holiday_calendar_is_not_labeled_as_ordinary_day(tmp_path, cfg):
    cfg = dict(cfg, observation_start="2024-01-01", observation_end="2024-01-03")
    daily = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3),
                          "destination_country": ["Synthetic-country"] * 3,
                          "carrier": ["Synthetic-carrier"] * 3, "sales_qty": [0, 2, 4]})
    eda(daily, tmp_path, cfg)
    holiday = pd.read_csv(tmp_path / "eda_holidays.csv")
    assert holiday.holiday_group.tolist() == ["unknown"]
    assert holiday.labeled_route_days.iloc[0] == 3
    assert holiday.mean_quantity.iloc[0] == 2
    assert (tmp_path / "figures" / "holidays.png").is_file()
