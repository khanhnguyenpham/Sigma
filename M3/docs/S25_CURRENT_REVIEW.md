# CHG-086 — Kiểm S25 trên chính sách hiện tại

**Cập nhật kế hoạch CHG-087 — 03/11/2026:** người dùng chọn demo đầy đủ cho project thực tập, mọi khách thao tác chung; [kế hoạch Render/Vercel](../../docs/planning/RENDER_VERCEL_DEPLOYMENT_PLAN.md) thay hướng chỉ đọc trước đó. Lượt này chỉ chỉnh/publishMD, không chạy lại phép kiểmS25 hoặc đưaS25 vào app. Kết quả/khuyến nghị chất lượng trong báo cáo giữ nguyên.

**03/11/2026 — Đã kiểm local; khuyến nghị giữ C00 làm mặc định.** S25 tăng số ca báo sớm, giảm nhẹ sai lệch ngày cạn trung bình, nhưng tăng lượng cảnh báo sai và làm giảm precision. Người dùng cho phép không ép45% nếu đánh đổi chất lượng không phù hợp; đây là thay đổi ưu tiên sản phẩm do người dùng, không phải xác nhận mới của mentor. Không đặt thêm một ngưỡng precision/MAE tùy ý để tự nghiệm thu R07/T14.

## 1. Phép kiểm và phạm vi

- Đối chiếu lại bằng chứng CHG-078 sealed: hash manifest/artifact, mã runner/verifier gốc, scalar projection và episode scoring vẫn khớp. Digest ứng dụng cũ khác hiện tại, được giữ đúng là bằng chứng lịch sử; không chạy lại verifier cũ rồi ghi đè receipt để giả tương thích.
- S25 = đường tiêu thụ stress bằng forecast14 ×1,25, C00 ×1. Đây là cơ chế cảnh báo riêng, không phải mô hình dự báo mới, xác suất hoặc khoảng tin cậy. Không nhân actual, sửa forecast nguồn hoặc dùng đường stress để đặt hàng.
- Phép kiểm mới dùng **920 policy hiện đang có trên app**, fixed ROP, SS days, fixed order quantity, cover7/safety multiplier1, L7/R1/H14. Cùng bộ đầu vào/forecast frozen validation/test đã kiểm; không refit, phân bổ lại, chọn alpha, sửa model hoặc tạo run trong DB app.
- Các tham số hiện tại được áp **phản thực lên lịch sử**; không nhận rằng policy đã tồn tại ở ngày quyết định năm2025. Validation/test đều đã được xem trong các nghiên cứu trước; đây là kiểm hồi cứu, không là holdout mới. Không lấy kết quả này thay kết quả alert replay không đặt mới của R07.
- Mỗi split dựng đường tồn bằng kernel hiện tại một lần; verifier scalar riêng dựng lại khởi tạo, từng sale/receipt/order/Q, ledger và alarm C00. C00/S25 giữ nguyên hash initialization/ledger/transactions/orders/events và cùng ID/ngày/sequence episode. Projection stress đối chiếu scalar, metric đối chiếu scorer độc lập.
- App có0 internal stop và0 provider notice tại lúc chụp. Phép kiểm dùng profile trade_v2 với lịch sử rỗng, **không chứng minh tích hợp S25 với ngừng bán/cap/exclusions**. Trước khi mở tính năng production phải có kiểm riêng quyền bán frozen, notice chồng lấp và mẫu số bị loại; không gắn hàm nghiên cứu trực tiếp vào worker.

## 2. Định nghĩa metric

Episode cạn là chuyển từ tồn dương sang0 sau giao dịch; cạn lại sau nhập/tồn dương là episode khác. Giữ28ngày warmup: validation chấm29/07–30/09/2025, test29/10–31/12/2025. Early khi cảnh báo hợp lệ sớm nhất gắn với episode đầu tiên trong14ngày kế tiếp, actual_lead≥7; stock đang0 không được tính thành cảnh báo sớm tương lai. Cảnh báo chỉ dùng receipts đã biết trước quyết định, không tính lô vừa khuyến nghị cùng ngày.

Precision = TP/(TP+FP) theo **item-ngày cảnh báo**, không phải số episode. Các ca có can thiệp nhập mà chưa thấy cạn và các ngày cuối chưa đủH14 giữ riêng; không đổi thành FP để làm đẹp so sánh. Recall/early tính theo episode. Date MAE là chênh lệch tuyệt đối giữa ngày cạn dự kiến tại cảnh báo hợp lệ sớm nhất và ngày episode, chỉ trên ca có cảnh báo; luôn ghi số ca được ghép. Ngày cạn dự kiến từ đường stress không được gọi là forecast điểm đã cải thiện. Tín hiệu xuống ROP có metric riêng, không cộng vào tử số depletion.

## 3. Kết quả mới — ROP cố định

| Kỳ | Phương án | Báo sớm≥7ngày | Precision | TP / FP item-ngày | Alarm/ngày | Date MAE (số episode ghép) | P90 / max sai lệch ngày |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Validation | C00 | 451/818 =55,13% | 76,58% | 4.398 /1.345 | 108,20 | 3,934 (664) | 8 /13 |
| Validation | S25 | 512/818 =62,59% | 68,35% | 5.219 /2.417 | 145,33 | 3,922 (701) | 9 /13 |
| Test hồi cứu | C00 | 450/833 =54,02% | 80,89% | 4.852 /1.146 | 118,88 | 4,011 (666) | 8 /13 |
| Test hồi cứu | S25 | 523/833 =62,79% | 74,30% | 5.761 /1.993 | 154,28 | 3,879 (696) | 8 /13 |

Validation thêm61episode early, không mất ca early cũ; test thêm73, không mất ca early cũ. Test FP tăng847item-ngày (+73,91%), alarm/ngày tăng29,78%; precision giảm6,60điểm phần trăm. Các đơn vị episode và item-ngày khác nhau; không coi847/73 là chi phí kinh doanh mỗi ca cảnh báo. Chưa có số liệu chi phí bỏ sót/phiền nhiễu thực để tính net benefit.

Test recall tăng666/833=79,95% lên696/833=83,55%. Intervened C00/S25=555/669; right-censored=1.055/1.451. Validation tương ứng513/640 và669/1.025. Không gọi các nhóm này là cảnh báo sai đã xác định.

Tập episode ghép được thay đổi, nên kiểm thêm **cùng666episode test có cảnh báo ở cả hai bên**: MAE4,011→3,758ngày; bias có dấu (ngày dự kiến−ngày cạn) +1,557→−0,068ngày. Cùng664episode validation: MAE3,934→3,745ngày, bias+1,145→−0,179ngày. Đây là cải thiện nhỏ về ngày trên tập ghép chung; P90 test toàn tập vẫn8ngày. Bias gần0 không loại bỏ sai lệch lớn từng ca.

## 4. Theo sản phẩm — kỳ test hồi cứu

Mỗi hàng gộp các tuyến/kho cùng SKU × loại; không phải cam kết chất lượng cho từng item. Cột date là MAE ngày và số episode ghép, C00→S25. Precision vẫn theo item-ngày; mẫu số episode ở cột n không dùng tính precision. `—` là không có ca chấm, không phải0 hoặc100%.

| SKU / loại | n episode | Early C00→S25 | Precision C00→S25 | Date MAE (support) C00→S25 |
| --- | --- | --- | --- | --- |
| D10G-10D / eSIM | 97 | 64 → 74 | 86.49% → 77.92% | 3.96 (92) → 3.54 (94) |
| D10G-10D / physical_SIM | 25 | 16 → 16 | 82.35% → 73.64% | 3.68 (19) → 3.00 (19) |
| D15G-15D / eSIM | 70 | 43 → 50 | 79.34% → 75.21% | 4.34 (59) → 4.63 (62) |
| D15G-15D / physical_SIM | 14 | 5 → 5 | 63.04% → 60.34% | 5.14 (7) → 4.57 (7) |
| D1G-3D / eSIM | 68 | 37 → 43 | 83.08% → 75.43% | 4.14 (57) → 3.84 (61) |
| D1G-3D / physical_SIM | 18 | 5 → 5 | 76.74% → 79.52% | 3.50 (6) → 5.88 (8) |
| D20G-30D / eSIM | 57 | 34 → 37 | 81.01% → 77.42% | 3.86 (43) → 4.00 (46) |
| D20G-30D / physical_SIM | 10 | 1 → 1 | 15.00% → 22.73% | 2.00 (1) → 0.00 (1) |
| D3G-5D / eSIM | 87 | 44 → 54 | 80.94% → 73.76% | 4.07 (75) → 4.09 (78) |
| D3G-5D / physical_SIM | 18 | 10 → 10 | 68.18% → 57.58% | 3.29 (14) → 3.00 (14) |
| D5G-7D / eSIM | 98 | 58 → 70 | 88.63% → 81.69% | 3.88 (91) → 3.57 (92) |
| D5G-7D / physical_SIM | 27 | 20 → 22 | 92.98% → 80.85% | 3.65 (23) → 3.58 (24) |
| UL-15D / eSIM | 53 | 25 → 31 | 70.86% → 66.67% | 4.61 (41) → 4.36 (44) |
| UL-15D / physical_SIM | 10 | 0 → 0 | 54.55% → 37.50% | 1.00 (1) → 2.00 (1) |
| UL-30D / eSIM | 27 | 14 → 15 | 79.57% → 66.39% | 3.89 (19) → 3.58 (19) |
| UL-30D / physical_SIM | 3 | 0 → 0 | — → — | — (0) → — (0) |
| UL-5D / eSIM | 56 | 27 → 35 | 84.41% → 78.71% | 3.65 (49) → 3.37 (52) |
| UL-5D / physical_SIM | 10 | 2 → 2 | 56.60% → 47.76% | 6.00 (4) → 6.00 (4) |
| UL-7D / eSIM | 69 | 37 → 45 | 79.28% → 75.75% | 4.12 (56) → 4.26 (61) |
| UL-7D / physical_SIM | 16 | 8 → 8 | 64.15% → 52.94% | 3.78 (9) → 3.33 (9) |

Ví dụ D1G-3D physical_SIM không tăng early (5/18), MAE3,50→5,88ngày; D15G-15D eSIM tăng early43→50/70 nhưng MAE4,34→4,63ngày. UL-30D physical_SIM chỉ3episode và0ca ghép nên không đủ kết luận về sai số. Không bỏ các nhóm yếu khỏi mẫu số hoặc chọn alpha riêng sau khi xem test. Mọi so sánh MAE theo hàng có thể chịu ảnh hưởng tập ca ghép khác nhau; bảng không được dùng để tự chọn SKU bật S25 production.

## 5. Kết quả S25 cũ — giữ riêng lịch sử

CHG-078 dùng fixed lot nhưng **ROP theo forecast**, khác policy app hiện tại. Kiểm lại nguyên sealed output cho thấy:

| Kỳ cũ | Early C00→S25 | Precision C00→S25 | FP C00→S25 |
| --- | --- | --- | --- |
| Validation | 104/366=28,42% →172/366=46,99% | 75,74% →56,61% | 294→1.241 |
| Test | 129/400=32,25% →196/400=49,00% | 74,06% →59,62% | 406→1.263 |

Các số này giải thích vì sao không chỉ nhìn việc S25 vượt45%. Mẫu số833 mới so với400 cũ đến từ **đường policy ROP khác**, không là cải thiện cùng cohort. Hash/mẫu số chỉ bất biến giữa C00 và S25 **trong mỗi phép kiểm**, không giữa hai thế hệ policy.

## 6. Quyết định sản phẩm và việc tiếp theo

Giữ C00 làm mặc định ở lượt này; chưa tích hợp hoặc bật S25 trong app. S25 có thể làm chế độ stress tùy chọn sau khi người dùng chốt mức chấp nhận cảnh báo sai, sai lệch ngày và gánh nặng xử lý theo sản phẩm. Không cần đạt45% bằng mọi giá; cũng không gọi C00 đã nghiệm thu chỉ vì early tổng trên45%. Không đổi M05/R05 hoặc mốc≥7ngày.

Bản demo công khai theoCHG087 giữC00 mặc định, có dữ liệu/kết quả ban đầu và cho khách tạo run mới, chỉnh cấu hình trên bộdemo chung đã ẩn danh. Trình bày ngày cạn như ước tính mô phỏng/H14, tránh cam kết đúng từng ngày; khi bậtstress sau này phải phân biệt với forecast điểm. Chưa chứng minh giá trị vận hành thật, chưa có tồn/nhập doanh nghiệp hoặc hiệu quả ngăn cạn. [Kế hoạch Render/Vercel hiện hành](../../docs/planning/RENDER_VERCEL_DEPLOYMENT_PLAN.md) đã bỏ giai đoạn chỉ đọc bắt buộc; việc triển khai sẽ làm sau lượtMD này.

## 7. Tái kiểm và bằng chứng

Mã nghiên cứu đã tạo local: `web/backend/research/current_s25_review.py`, `current_s25_verification.py`; test synthetic `web/backend/tests/test_current_s25_review.py`. **Ba tệpPython này chưa được publish trong commit chỉMD củaCHG087**; các lệnh dưới dùng bản local đã kiểm, không nhận checkout commitMD là đủ để chạy lại. Runner dùng lại loader, projection và scorer hiện có; chỉ tạo adapter current fixed policy, không sửa module nghiên cứu cũ. Chạy pytest không cần private input cho5ca mới. Full replay cần nguồn frozen và lock local đã kiểm; không tự truy cập hoặc ghi DB từ CLI nghiên cứu.

```powershell
.venv-m3/Scripts/python.exe -B tmp/supplier_checks.py -m pytest web/backend/tests/test_current_s25_review.py -q
.venv-m3/Scripts/python.exe -B tmp/supplier_checks.py -m web.backend.research.current_s25_review --run-dir outputs/chg086_s25_review
```

Lệnh replay từ chối thư mục đã có `summary.json`; không chạy lại vào bằng chứng này. Muốn tái kiểm phải khóa thư mục mới với source/policy/code hashes, cùng protocol, giữ kết quả cũ. `supplier_checks.py` là launcher local ignored để nạp/redact env, không là phụ thuộc triển khai; môi trường khác đặt PYTHONPATH và cấu hình tương đương. Chuẩn bị snapshot hiện tại là truy vấn chỉ đọc, dùng920policy; không áp ngược ngày hiệu lực trong DB.

Receipt riêng tư tại `outputs/chg086_s25_review/`: lock/policy/before, historical-audit, physical/alarms/cases/summary, verification, product-diagnostics, tests và preserved. Không đưa raw/run/DB/env/output vào Git hoặc cloud. [Bàn giao kiểm và bảo toàn](../../docs/development.md#handoff-chg086). Các metric này kiểm thuật toán và phép chấm hồi cứu, không tự đóng R07/T14.
