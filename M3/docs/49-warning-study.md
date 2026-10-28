# Nghiên cứu cảnh báo S25 đạt early 49,3080%

Điểm bắt đầu cho nhóm trên nhánh `codex/early-warning-opportunity-audit`. Ngày 28/10/2026, người dùng cho phép đẩy riêng mã/protocol/tests/tài liệu nghiên cứu để nhóm kéo về. Quyền mới thay phạm vi chỉ local của các checkpoint F1–F4; chưa lựa chọn S25 thay phương án chính `m3-implementation`, chưa tích hợp BE/FE, merge hoặc deploy.

## Kết quả và đánh đổi

S25 dùng `f' = 1,25 × f` cho đường cảnh báo H14. Mô hình gốc, tồn đầu, ledger, đơn nhập, receipts và episode của policy cơ sở giữ nguyên. Không đưa forecast stress trở lại tính Q hoặc sinh đơn nhập mới.

| Kỳ | C00 early | S25 early | Precision C00 | Precision S25 | FP C00 | FP S25 |
|---|---:|---:|---:|---:|---:|---:|
| Validation | 151/486 = 31,0700% | 228/486 = 46,9136% | 76,2585% | 60,6383% | 382 | 1.369 |
| Test hồi cứu | 193/578 = 33,3910% | 285/578 = 49,3080% | 80,6202% | 66,7646% | 425 | 1.358 |

- Early là tỷ lệ episode cạn được alarm hợp lệ trước actual ít nhất 7 ngày, mỗi episode tính một lần; không phải accuracy dự báo quantity.
- S25 được khóa sau 13 ứng viên validation; F4 chỉ C00 và S25, không chọn lại theo test. Test vẫn hồi cứu, model gốc có lịch sử test-selected; không phải holdout độc lập.
- Test thêm 92 episode early, không mất early cũ. Trong 64 ngày chấm, FP tăng 933 item-ngày; signal tăng 4.808 → 8.411. Precision giảm, can thiệp/right-censor giữ riêng.
- Tính cả 29 origin trước chấm, signal test tăng 6.453 → 11.182, FP 603 → 1.953. Có 14/92 early mới bắt đầu bằng alarm trước chấm; không bỏ tải này khi nói lợi ích.
- Item daily H1–14 WAPE test tăng 137,7015% → 148,8596%. Không gọi S25 là forecast điểm tốt hơn hoặc đã giảm thiếu hàng.
- Chưa chốt mức FP/tần suất được chấp nhận hoặc phương án triển khai. R07/T14 chưa nghiệm thu.

Con số ứng dụng **34,391350% = 986/2.867** thuộc `alert_replay` với cửa sổ H14 khởi tạo lại. C00 **33,3910% = 193/578** của nghiên cứu dùng episode trên đường tồn liên tục và giai đoạn chấm riêng. So S25 với C00 cùng mẫu số578; không so trực tiếp với986/2.867.

Đọc [F3 và ma trận validation](research.md#forecast-postprocessing-f3), [F4 test](research.md#forecast-postprocessing-f4), [tải cảnh báo](research.md#forecast-alarm-burden).

## Kéo mã về

Từ checkout không có thay đổi đang làm dở:

```powershell
git fetch origin
git switch codex/early-warning-opportunity-audit
git pull --ff-only origin codex/early-warning-opportunity-audit
```

Nếu chưa có repository local:

```powershell
git clone --branch codex/early-warning-opportunity-audit --single-branch https://github.com/khanhnguyenpham/Sigma.git
cd Sigma
```

## Kiểm synthetic không cần dữ liệu riêng tư

Yêu cầu Python3.12 như backend. Từ project root, tạo môi trường nếu chưa có:

```powershell
python --version
python -m venv .venv-m3
.venv-m3/Scripts/python.exe -m pip install -r web/backend/requirements.txt
.venv-m3/Scripts/python.exe -m pip install --no-deps -e web/backend
.venv-m3/Scripts/python.exe -m pip check
```

Không cần env DB, raw orders, frontend hoặc output nghiên cứu thật cho các lệnh sau:

```powershell
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_postprocessing --check-protocol
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_postprocessing_validation --help
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_postprocessing_test --help
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_alarm_burden --help
.venv-m3/Scripts/python.exe -B -m pytest web/backend/tests/test_inventory_forecast_identity.py web/backend/tests/test_forecast_postprocessing.py web/backend/tests/test_forecast_postprocessing_validation.py web/backend/tests/test_forecast_postprocessing_test.py web/backend/tests/test_forecast_alarm_burden.py web/backend/tests/test_inventory_alert_opportunity_audit.py
```

Bộ trên có115ca tại lần kiểm công bố28/10/2026. Đây là kiểm logic bằng synthetic, không phải tự tính lại49% từ dữ liệu thật. CI backend cũng thu thập các tests này.

## Các tệp chính

| Thành phần | Tệp |
|---|---|
| Protocol13ID và luật chọn | [forecast-postprocessing-v1.json](../../web/backend/configs/forecast-postprocessing-v1.json) |
| F1 identity/provenance | [inventory_forecast_identity.py](../../web/backend/research/inventory_forecast_identity.py) |
| F2 hậu xử lý/chọn validation | [forecast_postprocessing.py](../../web/backend/research/forecast_postprocessing.py) |
| F2 scalar verifier | [forecast_postprocessing_verification.py](../../web/backend/research/forecast_postprocessing_verification.py) |
| F3 validation/report | [forecast_postprocessing_validation.py](../../web/backend/research/forecast_postprocessing_validation.py) |
| F3 verifier | [forecast_postprocessing_validation_verification.py](../../web/backend/research/forecast_postprocessing_validation_verification.py) |
| F4 test C00 và đại diện khóa | [forecast_postprocessing_test.py](../../web/backend/research/forecast_postprocessing_test.py) |
| F4 verifier | [forecast_postprocessing_test_verification.py](../../web/backend/research/forecast_postprocessing_test_verification.py) |
| Phân tích tải output có sẵn | [forecast_alarm_burden.py](../../web/backend/research/forecast_alarm_burden.py) |

Các CLI ở `web/backend/research` tách khỏi `web/backend/src`; ứng dụng không tự gọi chúng khi chạy API/worker. Không thay code đã khóa trong gói công bố này.

`.gitattributes` giữ nguyên byte các file nghiên cứu mới để Git không tự đổi newline làm sai code-lock. Điều này không thay thế yêu cầu đúng app source/lineage/hash và đường dẫn của native runner.

## Điều kiện tái lập kết quả thật

GitHub có mã, protocol, tests và tài liệu tổng hợp; **không có raw CSV, DB, env, snapshot đầu vào hoặc output run private**. Clone mới đọc mã/chạy synthetic được; pull không làm FE xuất hiện S25 hoặc tự tái lập49%.

Native cần đúng chuỗi bundle frozen cùng manifest/receipt/hash: parent validation/test → audit verified → F1 identity → F2 code-lock → F3 đủ13validation với selection S25/parameters khóa trước F4. Nếu chỉ verify F4 hoặc đọc tải thì cần thêm output F4 đã có. Danh sách bundle/hash ở [F1](research.md#forecast-identity-f1), [F2](research.md#forecast-postprocessing-f2), [F3](research.md#forecast-postprocessing-f3), [F4](research.md#forecast-postprocessing-f4). Đường `outputs/...` trong tài liệu là bằng chứng local, không có trên GitHub.

Manifest hiện pin lineage và một số đường dẫn tuyệt đối của máy đã chạy. Native runner chưa là bộ tái lập chỉ cần clone ở bất kỳ thư mục nào. Chuyển môi trường mà nguồn/đường không khớp thì dừng để chuẩn bị quy trình chuyển nguồn được kiểm riêng; không sửa sealed manifest, bỏ kiểm hash hoặc tạo bundle giả để vượt source gate. Các lệnh sau là giao diện native cho môi trường có đúng đầu vào, không phải smoke chạy được trên clone sạch:

```powershell
# Kiểm lại F4 có sẵn khi lineage local đầy đủ
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_postprocessing_test verify --run-dir <F4_RUN>
# Chỉ khi chủ đích tái chạy và có đúng F3 khóa
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_postprocessing_test test --f3-run <F3_RUN> --output-root outputs/research/forecast-postprocessing-f4
# Phân tích tải từ output đã có, không sinh forecast
.venv-m3/Scripts/python.exe -B -m web.backend.research.forecast_alarm_burden --validation-run <F3_RUN> --test-run <F4_RUN>
```

Thay placeholder bằng đường local đã kiểm. Không thay alpha, grid, parameter, selection, cohort hoặc luật chấm theo kết quả test. Tái chạy native là công việc riêng có chi phí; không cần chạy để xem xét mã và đánh đổi hiện tại.

## Phạm vi giữ nguyên

- BE/FE, model gốc, DB/schema, scheduler và cấu hình mặc định không thay.
- Không đưa Word, ảnh FE, raw, run, DB hoặc env lên GitHub trong gói này.
- Chưa merge/deploy hoặc chọn S25 làm phương án chính. [Bàn giao công bố](../../docs/development.md#handoff-chg075-publish49).
