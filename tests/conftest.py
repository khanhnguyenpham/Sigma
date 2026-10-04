from copy import deepcopy

import pandas as pd
import pytest

from src.common import read_config
from src.data import SOURCE_COLUMNS


@pytest.fixture
def cfg():
    return deepcopy(read_config())


@pytest.fixture
def order_rows():
    # All IDs and data below are synthetic; never copied from source orders.
    row = dict.fromkeys(SOURCE_COLUMNS, "fixture")
    row.update(order_id="synthetic-1", customer_id="synthetic-customer", order_datetime="2024-02-29T23:30:00Z",
               activation_datetime="", destination_country="Testland", carrier="TestCarrier",
               sku="SYN-1", product_type="eSIM", quantity="3", unit_price_vnd="100",
               unit_cost_vnd="50", gross_revenue_vnd="300", data_gb="5", validity_days="7", order_status="success")
    return [row]


@pytest.fixture
def write_orders(tmp_path):
    def write(rows):
        path = tmp_path / "synthetic_orders.csv"
        pd.DataFrame(rows, columns=SOURCE_COLUMNS).to_csv(path, index=False)
        return path
    return write
