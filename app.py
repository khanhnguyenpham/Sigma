"""Local dashboard: consumes one sealed run; does not silently train models."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.common import ROOT, ROUTE, validate_run

st.set_page_config(page_title="SIGMA • Dự báo bán", page_icon="📈", layout="wide")
st.title("SIGMA · Dự báo bán và tồn mô phỏng")
st.caption("Quantity theo ngày UTC · Dữ liệu snapshot hồi cứu · Tồn và nhập hàng là mô phỏng")

run_root = ROOT / "outputs"
folders = sorted([p for p in run_root.glob("*") if p.is_dir() and (p / "manifest.json").is_file()], key=lambda p: p.name, reverse=True)
if not folders:
    st.info("Chưa có bộ kết quả. Chạy pipeline local theo README để tạo run; demo dùng dữ liệu giả.")
    st.stop()
preferred = os.environ.get("SIGMA_RUN_ID")
names = [p.name for p in folders]
index = names.index(preferred) if preferred in names else 0
name = st.sidebar.selectbox("Bộ kết quả", names, index=index)
folder = run_root / name
try:
    manifest = validate_run(folder)
except (OSError, ValueError, KeyError) as error:
    st.error(f"Không thể mở run: {error}. Chọn run hoàn tất và đúng hash; không dùng gói bị sửa hoặc thiếu.")
    st.stop()


@st.cache_data(show_spinner=False)
def table(path, expected_hash):
    # Cache key includes the hash sealed by the manifest.
    return pd.read_csv(path)


def load(name):
    return table(str(folder / name), manifest["files"][name])


@st.cache_data(show_spinner=False)
def filtered_table(path, expected_hash, destination, carrier):
    chunks = []
    for chunk in pd.read_csv(path, chunksize=50000):
        chunks.append(chunk.loc[chunk.destination_country.eq(destination) & chunk.carrier.eq(carrier)])
    return pd.concat(chunks, ignore_index=True)


def load_route(name):
    return filtered_table(str(folder / name), manifest["files"][name], country, carrier)


cfg = manifest["config"]
daily = load("daily_sales.csv")
daily["date"] = pd.to_datetime(daily.date)
routes = daily[ROUTE].drop_duplicates().sort_values(ROUTE)
country = st.sidebar.selectbox("Điểm đến", sorted(routes.destination_country.unique()))
carrier = st.sidebar.selectbox("Nhà mạng", sorted(routes.loc[routes.destination_country.eq(country), "carrier"].unique()))
origin = st.sidebar.radio("Origin dự báo", [cfg["forecast_origin"], cfg["demo_origin"]])
st.sidebar.caption(f"Run: {manifest['run_id']}\n\nTạo: {manifest['created_at_utc']}\n\nMode: {manifest['execution_mode']}")
st.sidebar.warning("A08–A17: người dùng chọn thực nghiệm, chưa phải mentor xác nhận tham số.")
if manifest["execution_mode"] == "baseline_demo":
    st.warning("Đây là MVP/demo baseline. Chưa chạy SARIMA/LightGBM trong run này.")
if manifest["source_kind"] == "generated_synthetic":
    st.info("Toàn bộ dữ liệu của run này được sinh giả để demo; không chứng minh chất lượng sales thực.")
if not manifest["accuracy_criterion_passed"]:
    st.warning("Run phần mềm đã hoàn tất; còn tiêu chí độ chính xác top 10 chưa đạt. Xem tab Đánh giá.")


def chosen(frame):
    return frame.loc[frame.destination_country.eq(country) & frame.carrier.eq(carrier)]


tabs = st.tabs(["Bán & dự báo", "Đánh giá", "Tồn & đặt hàng", "Cảnh báo", "Kịch bản", "Audit & giới hạn"])
with tabs[0]:
    forecast = chosen(load("forecast.csv" if origin == cfg["forecast_origin"] else "demo_forecast.csv"))
    forecast["target_date"] = pd.to_datetime(forecast.target_date)
    actual = chosen(daily).set_index("date").sales_qty
    start = pd.Timestamp(origin) - pd.Timedelta(days=60)
    chart = actual.loc[start:pd.Timestamp(origin)].rename("Actual quantity").to_frame()
    chart = chart.join(forecast.set_index("target_date").forecast_qty.rename("Forecast quantity"), how="outer")
    st.subheader(f"{country} · {carrier}")
    st.caption(f"Origin sau chốt ngày UTC: {origin} · Horizon {cfg['horizon']} ngày · Đơn vị: sản phẩm")
    st.line_chart(chart)
    columns = st.columns(3)
    columns[0].metric("Forecast 14 ngày", f"{forecast.forecast_qty.sum():.1f}")
    columns[1].metric("Mô hình", forecast.model.iloc[0])
    columns[2].metric("Ngày có actual trong horizon", int(forecast.actual_qty.notna().sum()))
    st.dataframe(forecast, hide_index=True, width="stretch")
    st.caption("Actual chưa có được để trống. Activation tháng 01/2026 không được dùng làm actual sales.")
with tabs[1]:
    metrics = chosen(load("metrics.csv"))
    group = st.selectbox("Nhóm horizon", ["h1_7", "h8_14"] + [f"h{i}" for i in range(1, 15)])
    st.dataframe(metrics.loc[metrics.horizon_group.eq(group)], hide_index=True, width="stretch")
    st.subheader("Nghiệm thu từng tuyến top 10 train · test h1–7")
    st.dataframe(load("accuracy_acceptance.csv"), hide_index=True, width="stretch")
    st.caption("MAPE chỉ ngày actual dương; MAE/WAPE/bias chấm mọi cặp có nhãn. Nhiều origin cùng ngày không là các ngày độc lập.")
    st.subheader("Lựa chọn bằng validation đã khóa")
    st.dataframe(chosen(load("selected_models.csv")), hide_index=True, width="stretch")
with tabs[2]:
    rec = load_route("inventory_recommendations.csv")
    rec = rec.loc[rec.scenario_id.eq("base") & rec.as_of_date.eq(origin)]
    st.caption("Tồn/nhập mô phỏng; trigger on-hand < ROP. IP dùng tính Q. Khuyến nghị đã xét hàng đang về.")
    st.dataframe(rec, hide_index=True, width="stretch")
    ledger = load_route("inventory_ledger.csv")
    ledger = ledger.loc[ledger.scenario_id.eq("base")]
    ledger["date"] = pd.to_datetime(ledger.date)
    st.line_chart(ledger.groupby("date")[["closing", "shortage"]].sum())
    st.dataframe(ledger.tail(100), hide_index=True, width="stretch")
with tabs[3]:
    st.subheader("Bất thường sau khi quan sát bán/doanh thu")
    anomalies = chosen(load("observed_anomalies.csv"))
    st.dataframe(anomalies.tail(100), hide_index=True, width="stretch")
    st.caption("Chẩn đoán không tự sửa actual, không khẳng định nguyên nhân và không dự đoán trước sự kiện chưa có tín hiệu.")
    st.subheader("Replay cảnh báo · đợt 14 ngày không chồng lấn, không đặt mới")
    st.dataframe(chosen(load("alerts.csv")), hide_index=True, width="stretch")
with tabs[4]:
    st.caption("Bán giảm/tăng và hàng nhận thiếu/trễ là các kịch bản giả định riêng; không sửa CSV hoặc forecast chọn bằng test.")
    st.dataframe(load("simulation_metrics.csv"), hide_index=True, width="stretch")
    st.json(json.loads((folder / "scenario_configs.json").read_text(encoding="utf-8")), expanded=False)
with tabs[5]:
    st.json(json.loads((folder / "data_audit.json").read_text(encoding="utf-8")), expanded=False)
    st.json({"source_kind": manifest["source_kind"], "source_sha256": manifest["source_sha256"],
             "code_sha256": manifest["code_sha256"], "packages": manifest["packages"],
             "snapshot_limit": manifest["snapshot_limit"], "missing_sources": manifest["missing_requirement_sources"]}, expanded=False)
    st.dataframe(load("inventory_issues.csv"), hide_index=True, width="stretch")
    export_allowed = st.checkbox("Tôi xác nhận có quyền xuất dữ liệu dẫn xuất này để dùng local", value=False)
    if export_allowed:
        st.download_button("Tải forecast tuyến đã chọn (CSV)", forecast.to_csv(index=False), file_name="sigma_forecast.csv", mime="text/csv")
