"""Public M3 workspace: verified results and isolated, deterministic what-if."""

from datetime import date
import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from sigma_public import runtime
from sigma_public.planner import plan

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "Tổng quan",
    "Dự báo",
    "Tồn kho",
    "Nhập hàng",
    "Cảnh báo",
    "Thử phương án",
    "Kiểm chứng",
]
LABELS = {
    "destination_country": "Quốc gia",
    "carrier": "Nhà mạng",
    "sku": "SKU",
    "product_type": "Loại",
    "date": "Ngày UTC",
    "as_of_date": "Origin UTC",
    "window_start": "Từ ngày",
    "target_date": "Đến ngày",
    "forecast_qty": "Dự báo",
    "actual_qty": "Actual",
    "model": "Mô hình",
    "model_id": "Mô hình",
    "mape_positive_pct": "MAPE (%)",
    "mae": "MAE",
    "wape_pct": "WAPE (%)",
    "bias": "Bias",
    "coverage": "Độ phủ",
    "n_scored_pairs": "Cửa sổ chấm",
    "passes_20_pct": "Đạt ≤20%",
    "sales_qty": "Lượng bán",
    "opening_qty": "Tồn đầu",
    "receipts_qty": "Nhập trong ngày",
    "fulfilled_qty": "Đã đáp ứng",
    "shortage_qty": "Thiếu",
    "closing_qty": "Tồn cuối",
    "ss": "Safety stock",
    "rop": "ROP",
    "target_stock": "Tồn mục tiêu S",
    "pending_qty": "Hàng đang về",
    "inventory_position": "IP",
    "recommended_qty": "Đề xuất Q",
    "configured_rop_floor": "ROP tối thiểu",
    "moq": "MOQ",
    "safety_days": "Safety (ngày)",
    "supplier": "Đối tác giả định",
    "ordered_on": "Ngày đặt nhập",
    "eta": "ETA nhập kho",
    "ordered_qty": "Đã đặt",
    "received_qty": "Đã nhận",
    "status": "Trạng thái",
    "state": "Mức cảnh báo",
    "predicted_depletion_date": "Dự kiến cạn",
    "actual_depletion_date": "Ngày cạn replay",
    "lead_days": "Ngày báo trước dự kiến",
    "evaluation_class": "TP/FP/FN/TN",
    "is_evaluable": "Đủ điều kiện chấm",
    "needs_replenishment": "Tồn dưới ROP",
    "metric_eligible": "Đủ cửa sổ chấm",
    "block": "Khối 7 ngày",
}


@st.cache_data(max_entries=20, show_spinner=False)
def decoded(data, spec):
    return runtime.decode_table(data, spec)


@st.cache_resource(show_spinner=False)
def decoded_cube(data):
    return runtime.decode_cube(data)


def fmt(value, digits=2):
    return (
        "—"
        if value is None or pd.isna(value)
        else f"{float(value):,.{digits}f}".replace(",", "_")
        .replace(".", ",")
        .replace("_", ".")
    )


def cards(values):
    for col, (label, value, detail) in zip(st.columns(len(values)), values):
        with col:
            st.metric(label, value)
            st.caption(detail)


def view(frame, columns=None):
    if columns:
        frame = frame[[c for c in columns if c in frame]]
    if frame.empty:
        st.info("Không có bản ghi phù hợp với bộ lọc.")
    else:
        st.dataframe(frame.rename(columns=LABELS), hide_index=True, width="stretch")


def main():
    st.set_page_config(
        page_title="SIGMA · Nhu cầu & tồn kho",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """<style>
    .block-container{padding-top:2rem;max-width:1500px}h1{color:#123e43;letter-spacing:-.035em}
    [data-testid="stMetric"]{border:1px solid #dbe6e7;border-top:3px solid #138477;border-radius:10px;padding:16px;background:#f7fbfa}
    [data-testid="stSidebar"]{background:#eff7f5} .stCaption{color:#557078}
    </style>""",
        unsafe_allow_html=True,
    )
    folder = ROOT / "release_m3"
    try:
        meta, pin = runtime.manifest(folder)
    except (OSError, ValueError, KeyError):
        st.error(
            "Gói M3 chưa hợp lệ hoặc checksum không khớp. Chưa thể hiển thị kết quả."
        )
        st.stop()

    def load(name):
        try:
            spec = meta["tables"][name]
            data = runtime.payload(folder, meta, spec["file"])
            return decoded(data, spec)
        except (OSError, ValueError, KeyError):
            st.error(
                "Bảng kết quả thiếu hoặc không khớp checksum. Không sử dụng dữ liệu cũ thay thế."
            )
            st.stop()

    def download(frame, name, scope):
        st.download_button(
            "↓ Tải CSV · " + name,
            runtime.csv_export(frame, meta, scope),
            file_name="sigma_" + name + ".csv",
            mime="text/csv",
            key="download_" + name,
        )

    catalog = load("catalog")
    st.sidebar.title("SIGMA")
    st.sidebar.caption("DEMAND & INVENTORY · M3")
    page = st.sidebar.radio("Màn hình", PAGES, key="m3_public_page")
    country = st.sidebar.selectbox(
        "Quốc gia", ["Tất cả"] + sorted(catalog.destination_country.unique().tolist())
    )
    scoped = (
        catalog
        if country == "Tất cả"
        else catalog[catalog.destination_country == country]
    )
    carrier = st.sidebar.selectbox(
        "Nhà mạng",
        ["Tất cả"] + sorted(scoped.carrier.unique().tolist()),
        key="carrier_" + country,
    )
    if carrier != "Tất cả":
        scoped = scoped[scoped.carrier == carrier]
    ptype = st.sidebar.selectbox("Loại sản phẩm", ["Tất cả", "eSIM", "physical_SIM"])
    if ptype != "Tất cả":
        scoped = scoped[scoped.product_type == ptype]
    sku = st.sidebar.selectbox(
        "SKU",
        ["Tất cả"] + sorted(scoped.sku.unique().tolist()),
        key="sku_" + country + carrier + ptype,
    )
    if sku != "Tất cả":
        scoped = scoped[scoped.sku == sku]
    origins = sorted(load("weekly").as_of_date.unique().tolist())
    origin = st.sidebar.selectbox(
        "Origin UTC", origins, index=origins.index("2025-10-31")
    )
    st.sidebar.divider()
    st.sidebar.caption(
        "Nguồn quan sát đến 31/12/2025 · L7 / R1 / H14 · tồn và nhập mô phỏng"
    )
    st.title("Dự báo nhu cầu & điều phối tồn kho")
    st.caption(
        "SIGMA / "
        + page
        + " · "
        + meta["version"]
        + " · nguồn A08: success theo ngày đặt UTC, chưa xác nhận kế toán"
    )
    item_keys = set(scoped.item_key)
    route_keys = set(zip(scoped.destination_country, scoped.carrier))

    def route_filter(frame):
        return frame[
            [
                tuple(r) in route_keys
                for r in frame[["destination_country", "carrier"]].to_numpy()
            ]
        ].copy()

    def item_filter(frame):
        return frame[frame.item_key.isin(item_keys)].merge(
            catalog, on="item_key", validate="many_to_one"
        )

    monthly_metrics = load("monthly_metrics")
    official = monthly_metrics[
        (monthly_metrics.split == "test")
        & (monthly_metrics.cadence == "daily_origins")
        & monthly_metrics.is_top10
    ]
    passed = int(
        (
            (official.mape_positive_pct <= 20)
            & (official.coverage == 1)
            & (official.n_positive_pairs > 0)
        ).sum()
    )
    if page == "Tổng quan":
        st.subheader("Từ dự báo đến quyết định nhập hàng")
        cards(
            [
                ("R05 · Tổng 30 ngày", f"{passed}/10", "Từng tuyến top 10 theo train"),
                (
                    "MAPE trung bình",
                    fmt(official.mape_positive_pct.mean()) + "%",
                    "63 cửa sổ test đầy đủ / tuyến",
                ),
                (
                    "Độ phủ tối thiểu",
                    fmt(official.coverage.min() * 100, 1) + "%",
                    "Cửa sổ D+1…D+30",
                ),
                ("Phạm vi", "46 tuyến", "920 SKU × loại sản phẩm"),
            ]
        )
        st.success(
            "M05: mentor do người dùng thuật lại đã chốt chấm tổng 30 ngày thay từng ngày. R05 đạt ngưỡng số học trên test hồi cứu."
        )
        st.markdown(
            "**01 · Dự báo:** tổng 30 cho R05; tổng 7 và ngày phân bổ cho vận hành H14.\n\n**02 · Tồn & nhập:** ROP riêng đối tác–mặt hàng, MOQ, safety stock, IP và ETA đúng D+7.\n\n**03 · Cảnh báo:** ngày cạn dự kiến; replay cảnh báo tách riêng replay có nhập hàng."
        )
        cards(
            [
                (
                    "Fill mô phỏng cơ sở",
                    fmt(meta["policy_metrics"]["fill_rate"] * 100) + "%",
                    "Policy replay có nhập mới",
                ),
                (
                    "Báo sớm ≥7 ngày",
                    fmt(meta["alert_metrics"]["early_rate"] * 100) + "%",
                    "986 / 2.867 sự kiện; mẫu không có nhập mới",
                ),
            ]
        )
        daily = route_filter(load("route_daily"))
        daily = daily.groupby("date", as_index=True).sales_qty.sum()
        st.subheader("Lượng bán lịch sử theo bộ lọc tuyến")
        st.line_chart(daily.rename("Lượng bán"))
        st.caption(
            "Biểu đồ cộng quantity theo tuyến; bộ lọc SKU/loại không phân rã actual ở màn hình này."
        )
    elif page == "Dự báo":
        mode = st.radio(
            "Phương pháp",
            ["Tổng 30 · R05", "Tổng 7 · H14", "Ngày phân bổ · H14"],
            horizontal=True,
        )
        st.info(
            "Top 10 xếp theo train. Test hồi cứu; 63 cửa sổ chồng nhau không phải 63 mẫu độc lập. Metric toàn kỳ, không phụ thuộc origin đang xem."
        )
        if mode == "Tổng 30 · R05":
            cards(
                [
                    (
                        "R05 toàn bộ top 10",
                        f"{passed}/10",
                        "Không đổi mẫu số theo bộ lọc",
                    ),
                    (
                        "MAPE top 10",
                        fmt(official.mape_positive_pct.mean()) + "%",
                        "Test 01/10–31/12/2025",
                    ),
                ]
            )
            top_only = st.checkbox("Chỉ top 10 train", value=True)
            forecasts = route_filter(load("monthly_forecasts"))
            forecasts = forecasts[forecasts.as_of_date == origin]
            metric = route_filter(monthly_metrics)
            metric = metric[
                (metric.split == "test") & (metric.cadence == "daily_origins")
            ]
            if top_only:
                forecasts, metric = (
                    forecasts[forecasts.is_top10],
                    metric[metric.is_top10],
                )
            st.subheader(f"Tổng 30 ngày sau origin {origin}")
            view(
                forecasts,
                [
                    "destination_country",
                    "carrier",
                    "window_start",
                    "target_date",
                    "forecast_qty",
                    "actual_qty",
                    "model",
                    "metric_eligible",
                ],
            )
            if len(forecasts):
                plot = forecasts.assign(
                    Tuyến=forecasts.destination_country + " / " + forecasts.carrier
                ).set_index("Tuyến")
                st.bar_chart(
                    plot[["forecast_qty", "actual_qty"]].rename(columns=LABELS),
                    stack=False,
                )
            download(forecasts, "du_bao_30_ngay", "route/origin=" + origin)
            st.subheader("Sai số tổng 30 · test đầy đủ")
            view(
                metric,
                [
                    "destination_country",
                    "carrier",
                    "mape_positive_pct",
                    "mae",
                    "wape_pct",
                    "bias",
                    "coverage",
                    "n_scored_pairs",
                    "passes_20_pct",
                ],
            )
            download(metric, "sai_so_30_ngay", "test/daily_origins")
            baseline = (
                load("baselines")
                .groupby("model", as_index=False)
                .agg(
                    MAPE=("mape_positive_pct", "mean"),
                    Số_tuyến_đạt=("mape_positive_pct", lambda x: (x <= 20).sum()),
                )
            )
            st.subheader("Baseline cùng 63 cửa sổ · toàn bộ top 10")
            view(baseline)
        elif mode == "Tổng 7 · H14":
            forecasts = route_filter(load("weekly"))
            forecasts = forecasts[forecasts.as_of_date == origin]
            view(
                forecasts,
                [
                    "destination_country",
                    "carrier",
                    "block",
                    "window_start",
                    "target_date",
                    "forecast_qty",
                    "actual_qty",
                    "model_id",
                ],
            )
            download(forecasts, "du_bao_7_ngay", "route/origin=" + origin)
            metric = route_filter(load("weekly_metrics"))
            metric = metric[
                (metric.split == "test") & (metric.cadence == "daily_origins")
            ]
            view(
                metric,
                [
                    "destination_country",
                    "carrier",
                    "block",
                    "mape_positive_pct",
                    "mae",
                    "wape_pct",
                    "bias",
                    "coverage",
                    "n_scored_pairs",
                ],
            )
            st.caption(
                "Tổng tuần vận hành gồm final10 và 36 tuyến mở rộng; không gọi toàn bộ 46 tuyến đạt R05."
            )
        else:
            cube, cube_origins = decoded_cube(
                runtime.payload(folder, meta, "item_forecasts.npz")
            )
            selected = cube[list(cube_origins).index(origin), sorted(item_keys), :].sum(
                axis=0
            )
            timeline = pd.DataFrame(
                dict(
                    date=pd.date_range(
                        pd.Timestamp(origin) + pd.Timedelta(days=1), periods=14
                    ).strftime("%Y-%m-%d"),
                    forecast_qty=selected,
                )
            )
            st.line_chart(timeline.set_index("date").rename(columns=LABELS))
            view(timeline)
            st.caption(
                "Dự báo ngày dẫn xuất từ tổng tuần bằng weekday90/share30→90. Bộ lọc SKU/loại có hiệu lực; không gọi mô hình ngày độc lập."
            )
            download(timeline, "phan_bo_ngay_H14", "allocated_daily/origin=" + origin)
    elif page in {"Tồn kho", "Nhập hàng"}:
        options = [k for k in meta["runs"] if k.startswith("snapshot_")] + [
            "policy_base"
        ]
        selected_run = st.selectbox(
            "Lượt tồn mô phỏng",
            options,
            format_func=lambda x: {
                "snapshot_2025-10-31_pending": "31/10/2025 · có lô đang về",
                "snapshot_2025-12-31": "31/12/2025 · dự phóng tương lai",
                "policy_base": "Replay cơ sở · 01/10–31/12/2025",
            }[x],
        )
        st.caption(
            "Màn hình dùng snapshot/lượt đã chọn ở đây; origin chung bên trái không đổi lịch sử của snapshot."
        )
        if page == "Tồn kho":
            rows = load("inventory")
            rows = item_filter(rows[rows.run_label == selected_run])
            day = (
                st.selectbox("Ngày sổ tồn UTC", sorted(rows.date.unique().tolist()))
                if len(rows)
                else None
            )
            shown = rows[rows.date == day]
            cards(
                [
                    ("Mặt hàng trong bộ lọc", str(len(shown)), "Tồn và nhập giả định"),
                    (
                        "Tồn cuối",
                        fmt(shown.closing_qty.sum(), 0),
                        "Chưa cộng hàng đang về",
                    ),
                    (
                        "Đề xuất Q",
                        fmt(shown.recommended_qty.sum(), 0),
                        "IP và MOQ đã tính trong Q",
                    ),
                ]
            )
            view(
                shown,
                [
                    "destination_country",
                    "carrier",
                    "sku",
                    "product_type",
                    "closing_qty",
                    "ss",
                    "rop",
                    "pending_qty",
                    "inventory_position",
                    "moq",
                    "recommended_qty",
                    "needs_replenishment",
                ],
            )
            st.caption(
                "Trigger: closing < ROP. Bằng ROP không kích hoạt. IP=closing+pending chỉ dùng tính lượng đặt. Dưới ROP nhưng pending đủ có thể Q=0."
            )
            download(shown, "ton_kho", selected_run + "/date=" + str(day))
        else:
            rows = load("receipts")
            rows = item_filter(rows[rows.run_label == selected_run])
            st.subheader("Lịch đặt và nhận hàng mô phỏng")
            view(
                rows,
                [
                    "destination_country",
                    "carrier",
                    "sku",
                    "product_type",
                    "ordered_on",
                    "eta",
                    "ordered_qty",
                    "received_qty",
                    "status",
                ],
            )
            st.caption(
                "ETA=ngày đặt nhập+7 ngày lịch UTC, nhận đầu ngày. Ngày giao khách D+7 là khái niệm riêng. Không gửi đơn nhập thật."
            )
            download(rows, "lich_nhap_hang", selected_run)
    elif page == "Cảnh báo":
        m = meta["alert_metrics"]
        cards(
            [
                (
                    "Báo sớm ≥7 ngày",
                    fmt(m["early_rate"] * 100) + "%",
                    f"{m['early_numerator']} / {m['event_denominator']} sự kiện",
                ),
                ("Precision", fmt(m["precision"] * 100) + "%", "Replay không đặt mới"),
                (
                    "Recall",
                    fmt(m["recall"] * 100) + "%",
                    f"Loại {m['excluded_count']} ca đã cạn tại origin",
                ),
                (
                    "Sai số ngày cạn",
                    fmt(m["date_mae"]) + " ngày",
                    "Trên TP, không thay bằng 0 khi thiếu",
                ),
            ]
        )
        st.caption(
            "Các thẻ dùng toàn bộ replay cơ sở; bảng bên dưới áp dụng bộ lọc. Chưa có ngưỡng tỷ lệ tổng chính thức để tự nhận nghiệm thu R07."
        )
        rows = item_filter(load("alerts").query("run_label == 'alert_base'"))
        state = st.selectbox(
            "Mức cảnh báo", ["Tất cả"] + sorted(rows.state.unique().tolist())
        )
        if state != "Tất cả":
            rows = rows[rows.state == state]
        view(
            rows,
            [
                "destination_country",
                "carrier",
                "sku",
                "product_type",
                "as_of_date",
                "state",
                "predicted_depletion_date",
                "actual_depletion_date",
                "lead_days",
                "is_evaluable",
                "evaluation_class",
            ],
        )
        download(rows, "canh_bao_replay", "alert_base/state=" + state)
        d = meta["alert_opportunities"]
        st.warning(
            f"{d['short_notice_events']} sự kiện cạn trong D+1…6; còn {d['eligible_early_events']} ca đủ ít nhất 7 ngày, bỏ sót {d['missed_eligible_events']} ca. Đây là chẩn đoán sau replay; không dùng actual tương lai làm đầu vào dự báo."
        )
        st.subheader("Độ nhạy đã chạy · mỗi kịch bản có mẫu sự kiện riêng")
        view(load("scenarios"))
    elif page == "Thử phương án":
        st.subheader("Thử nhập hàng và biến động nhu cầu")
        st.caption(
            "Mô phỏng riêng từng phiên. Dùng forecast H14 đã kiểm và cùng hàm recommend/project của M3; không ghi database hoặc thay benchmark."
        )
        eligible = scoped[scoped.first_seen_date <= origin].copy()
        if eligible.empty:
            st.info("Mặt hàng chưa có lịch sử tại origin này.")
            st.stop()
        by_key = eligible.set_index("item_key")
        selected = st.selectbox(
            "Mặt hàng mô phỏng",
            list(by_key.index),
            format_func=lambda k: " / ".join(
                str(by_key.loc[k, c])
                for c in ["destination_country", "carrier", "sku", "product_type"]
            ),
        )
        item = by_key.loc[selected]
        cube, cube_origins = decoded_cube(
            runtime.payload(folder, meta, "item_forecasts.npz")
        )
        forecast = cube[list(cube_origins).index(origin), selected]
        # Widget state is scoped to origin+item, so old assumptions never leak into a new context.
        prefix = f"plan_{origin}_{selected}_"
        default_stock = int(np.ceil(forecast.mean() * 7))
        with st.form(prefix):
            left, right = st.columns(2)
            with left:
                stock = st.number_input(
                    "Tồn hiện có giả định",
                    0,
                    1000000000,
                    default_stock,
                    key=prefix + "stock",
                )
                pending = st.number_input(
                    "Lô đang về · đã biết tại origin",
                    0,
                    1000000000,
                    0,
                    key=prefix + "pending",
                )
                arrival = st.slider(
                    "Lô đang về đến sau bao nhiêu ngày", 1, 7, 7, key=prefix + "arrival"
                )
                moq = st.number_input(
                    "MOQ", 1, 1000000000, int(item.moq), key=prefix + "moq"
                )
            with right:
                floor = st.number_input(
                    "ROP tối thiểu đối tác",
                    0,
                    1000000000,
                    int(item.configured_rop_floor),
                    key=prefix + "floor",
                )
                safety = st.number_input(
                    "Safety stock · số ngày",
                    0.0,
                    30.0,
                    float(item.safety_days),
                    step=0.5,
                    key=prefix + "safety",
                )
                factor = st.slider(
                    "Lượng bán so với dự báo (%)",
                    0,
                    300,
                    100,
                    10,
                    key=prefix + "factor",
                )
                shock_days = st.slider(
                    "Số ngày biến động từ D+1", 1, 14, 7, key=prefix + "shock_days"
                )
                receive = st.slider(
                    "Tỷ lệ nhận hàng giả định (%)",
                    0,
                    100,
                    100,
                    10,
                    key=prefix + "receive",
                )
            submitted = st.form_submit_button("Tính phương án", type="primary")
        if submitted:
            st.session_state[prefix + "result"] = plan(
                date.fromisoformat(origin),
                forecast,
                int(stock),
                int(pending),
                int(arrival),
                int(floor),
                int(moq),
                float(safety),
                factor / 100,
                int(shock_days),
                receive / 100,
            )
        result = st.session_state.get(prefix + "result")
        if result:
            d = result["decision"]
            cards(
                [
                    ("ROP", fmt(d["rop"], 0), "max(floor, ceil(nhu cầu 7 ngày+SS))"),
                    (
                        "IP",
                        fmt(d["inventory_position"], 0),
                        "Tồn hiện có + lượng đã đặt",
                    ),
                    (
                        "Đề xuất Q",
                        fmt(d["recommended_qty"], 0),
                        "MOQ chỉ áp dụng nếu Q>0",
                    ),
                    ("ETA lô mới", result["proposed_eta"], "Luôn D+7, gồm cuối tuần"),
                ]
            )
            st.caption(
                f"Phương án đã tính: tồn={stock}, pending={pending}, nhu cầu={factor}%, nhận hàng={receive}%. Số dự kiến có thể lẻ; actual tương lai chưa có. Điểm chạm 0 thuộc horizon14; không dự báo ngày cạn ngoài horizon."
            )
            if d["state"] == "pending_covers":
                st.info(
                    "Tồn dưới ROP nhưng lượng đang về đã đủ mức mục tiêu: Q=0, tránh đặt trùng. ETA vẫn phải xem trên đường tồn; IP đủ không bảo đảm không cạn trước ngày nhận."
                )
            timeline = result["timeline"]
            st.line_chart(
                timeline.set_index("date")[
                    ["closing_without_order", "closing_with_order"]
                ].rename(
                    columns={
                        "closing_without_order": "Không đặt thêm",
                        "closing_with_order": "Có lô đề xuất",
                    }
                )
            )
            view(timeline)
            download(timeline, "phuong_an_H14", prefix)
    else:
        st.subheader("Nguồn, tiêu chí và giới hạn")
        st.markdown(
            "**M05:** tổng D+1…D+30, từng top10 train, MAPE actual dương≤20%, kèm coverage/MAE/WAPE/bias. Train 01/01/2024–30/06/2025; validation quý3/2025; test quý4/2025. Tổng30 hồi cứu; hướng focus được xác định sau khi đã xem test cũ.\n\n**M3:** 46 kho/tuyến giả định, 920 item, supplier-item có policy riêng; L7/R1/H14. Ledger nhập đầu ngày, strict closing<ROP, IP chỉ Q. Cảnh báo và policy replay tách riêng.\n\n**Phạm vi online:** xem kết quả đã kiểm, lọc, tải CSV và mô phỏng riêng từng phiên. Huấn luyện, nạp raw, worker/database bền vững và quản trị nhiều người dùng tiếp tục ở ứng dụng local. Không gọi dự báo 01/2026 là actual hoặc doanh số hiện tại năm2026."
        )
        st.code(
            "Source SHA256: "
            + meta["source_sha256"]
            + "\nManifest SHA256: "
            + pin
            + "\nMonthly benchmark: "
            + meta["benchmark_package_id"]
        )
        st.subheader("Các bảng công khai đã qua checksum")
        view(
            pd.DataFrame(
                [
                    dict(bảng=k, số_dòng=v["rows"], tệp=v["file"])
                    for k, v in meta["tables"].items()
                ]
            )
        )
        st.download_button(
            "↓ Tải thông tin phiên bản",
            json.dumps(
                {
                    k: meta[k]
                    for k in [
                        "version",
                        "profile",
                        "acceptance",
                        "source_sha256",
                        "monthly_summary_sha256",
                        "test_independent",
                        "runs",
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ).encode(),
            file_name="sigma_release_context.json",
            mime="application/json",
        )
    st.divider()
    st.caption(
        "SIGMA · Snapshot lịch sử 2024–2025 · Tồn/nhập mô phỏng · Chưa có holdout độc lập hoặc biên bản nghiệm thu toàn bài"
    )
