# SIGMA — hướng dẫn nộp và kiểm tra sản phẩm

**Hiện hành CHG-072 — 25/10/2026:** frontend ở web/frontend, configs/research code/env ở web/backend; M3 chỉ giữ Markdown và protocol nghiên cứu. Backend serve/build/launcher/CI đã đổi đường; tên env/DB, FE/nghiệp vụ/API/13bảng/snapshot giữ nguyên. [Cây thực](docs/05-source-architecture.md#web-layout-chg072), [bàn giao](../docs/development.md#handoff-chg072). Bước11–15 chưa bắt đầu; các mốc đường M3/frontend/configs/research/env dưới đây là lịch sử trước chuyển vị trí, các lệnh chạy đã cập nhật.

**CHG-068 — 24/10/2026, kế hoạch đã được người dùng duyệt:** nhánh `m3-implementation` từ `codex/m3-implementation` tại `b1357cd`; cập nhật tài liệu trước, bỏ toàn bộ Streamlit, tổ chức BE theo module/FE theo feature và thành phần dùng chung, sau đó thêm policy/cảnh báo cấu hình. Mỗi bước kiểm local → commit → push → SHA remote khớp → CI đạt trước bước sau. Code chưa thay đổi ở bước 1; các mốc E99 trở về trước bên dưới là bằng chứng lịch sử, không phải kiểm lại trong lượt này. Giữ M05 tổng30, H14/L7/R1, snapshot và dữ liệu local; R07/T14 chưa nghiệm thu.

Hướng bàn giao CHG-068 chuyển local React/FastAPI; nguồn public Streamlit bên dưới là hướng dẫn lịch sử E99 và chưa bị xóa ở bước tài liệu. Không upload dữ liệu hoặc deploy trong lượt này. Sau bước15 cập nhật lệnh đã kiểm, run/hash, commit/CI và vấn đề mở.

[Kế hoạch CHG-068 và cổng từng bước](../docs/planning/PLAN.md#chg-068).

Cập nhật21/10/2026, E99. [Mở ứng dụng công khai](https://sigma-demand-inventory.streamlit.app/) · [Mã nguồn React/Python](https://github.com/khanhnguyenpham/Sigma/tree/codex/m3-implementation) · [Cài và chạy local](IMPLEMENTATION.md) · [Phạm vi online](../docs/review-log.md#removed-docs-chg070).

## Nội dung nộp

Đưa link ứng dụng và nhánh `codex/m3-implementation` cho mentor. M3 gồm quản lý dự báo, tồn, kế hoạch bổ sung, lịch hàng về, cảnh báo và cấu hình mô phỏng. Sáu màn hình dùng React; online phục vụ aggregate đã kiểm qua Streamlit. Pipeline huấn luyện/API/PostgreSQL/worker đầy đủ chạy local theo IMPLEMENTATION; không mô tả là toàn bộ stack đã được triển khai cloud.

Ứng dụng có Hướng dẫn sử dụng trong header desktop và cuối trang, giải thích ROP/IP/MOQ, luồng thao tác, pending, CSV và dữ liệu chưa quan sát. Ngày trên thanh lọc là ngày nghiệp vụ UTC của bộ dữ liệu2024–2025, không phải ngày hệ thống hiện tại.

## Luồng kiểm nhanh trên web

| Bước | Thao tác | Kết quả để kiểm |
|---|---|---|
| 1 | Mở Tổng quan, chọn kế hoạch tồn kho31/10/2025 đã công bố, tất cả kho | 920mặt hàng/46tuyến, tồn1314;793mặt hàng cần đặt/5866đơn vị;1lô20đơn vị đang về |
| 2 | Tồn kho → Japan/NTT Docomo → D10G-10D/eSIM → mở dòng | Tồn7/ROP20/pending20/IP27/Q0; pending đủ không có nghĩa tồn hiện có đã tăng |
| 3 | Nhập hàng → Đang về | Lô20đơn vị đặt28/10, ETA04/11; nhận sau đúng7ngày. Đề xuất không gửi đơn thật |
| 4 | Dự báo nhu cầu → Tổng30 → mở Chất lượng & nguồn | Top10 theo train:10/10 MAPE≤20%, mean11,621356%, coverage100%,63cửa sổ/tuyến; baseline và giới hạn hồi cứu ghi rõ |
| 5 | Chuyển Tổng7 rồi Phân bổ theo ngày | Hai khối tuần phục vụ H14; tổng30 là luồng nhu cầu riêng, không chia đều để tính tồn |
| 6 | Chọn kế hoạch31/12/2025 → Dự báo | Actual sau31/12 trống/chưa đủ nhãn; không biến thành0 hoặc điểm sai số đã quan sát |
| 7 | Cảnh báo → chọn một dòng cạn | Có trạng thái, ngày cạn dự kiến và biểu đồ tồn14ngày; lô đã biết nhận đầu ngày ETA |
| 8 | Cấu hình → Kịch bản → tạo mới → Tạo phương án | Chỉ cho chọn ngày đủ dữ liệu. Kết quả mới giữ riêng phiên; cấu hình cũ và benchmark không đổi |
| 9 | Bấm Làm mới dữ liệu | Tải lại các bảng trong cùng phiên, không chủ động reset cấu hình/phương án |
| 10 | Xuất CSV rồi Tải CSV | Toàn bộ bản ghi đúng bộ lọc/context, không chỉ trang hiện tại; đổi bộ lọc phải xuất lại |

Khi thử phương án online cơ sở với danh sách lô trống, tồn đầu vẫn1314 nhưng pending0 và Q794mặt hàng/5871đơn vị. Đây là kết quả khác có lý do: không tự mang lô20đơn vị của snapshot đã công bố sang kịch bản mới. Để thử pending, phải khai báo đúng mặt hàng/ngày đặt/ETA/quantity trong kịch bản.

## Kiểm tra kỹ thuật

E99 chạy120testPython không lỗi/bỏ qua,31testReact đạt, build TypeScript/Vite cả hai chế độ. Bao gồm timeout đọc, không tự gửi lại write, late reply không gán sang context mới, ngày khả dụng, nguồn/error guards, pending/ETA/MOQ, CSV, isolation và hồi quyM2. Link, anchor, code fence và bảng Markdown được kiểm. CI của từng commit phải xem trạng thái thực trong [GitHub Actions](https://github.com/khanhnguyenpham/Sigma/actions); không suy từ tài liệu rằng CI mới đã thành công.

```powershell
# Trong web/frontend
npm ci
npm test
npm run build
npm run build:streamlit
```

Build thứ nhất cho FastAPI local; build thứ hai cho component Streamlit. Cách tạo nguồn, database và run trên máy thành viên theo IMPLEMENTATION. Repo không chứa raw, run thật, DB, env hoặc credentials. Dữ liệu public chỉ là aggregate đã rà, không có ID đơn/khách. Không copy UUID của run local để giả định máy khác đã có cùng dữ liệu.

## Giới hạn cần trình bày đúng

- R05 theo M05 chấm tổng30. Kết quả10/10 là đánh giá hồi cứu, không phải holdout độc lập chưa từng xem; ngày phân bổ không có cùng kết quả.
- Tồn, supplier mapping, nhập và lead time có giả định/mô phỏng. Chỉ order là dữ liệu được cung cấp. Quy tắc success theo order_datetime vẫn A08 đề xuất.
- Cấu hình và phương án online riêng phiên, có thể mất sau reset/ngủ/restart. Không có database dùng chung bền vững trên Streamlit.
- Online tạo stock_projection từ closing công bố tại origin và forecast đã khóa; không huấn luyện mới hoặc replay chuỗi giao dịch gốc. Không mở DB/FastAPI local ra Internet.
- Chưa có quy trình duyệt/gửi PO thật, nhận hàng thủ công hoặc phân quyền người dùng. Đây không phải các chức năng đã nghiệm thu trong phạm vi hiện tại.
- R07/T14 vẫn cần mentor chốt/kiểm nghiệm thu. Không đồng nhất việc build/test/deploy thành công với cam kết đạt mọi tiêu chí hoặc điểm số.
