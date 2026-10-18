# Triển khai SIGMA bằng địa chỉ trung tính

**Lịch sử chuẩn bị E80:** ngày 18/10/2026, người dùng yêu cầu bản dùng kết quả nguồn bài và không muốn URL mang tên nền tảng ChatGPT. Chưa có tên miền/hosting. Đã đăng nhập Streamlit; giao diện yêu cầu kết nối GitHub trước khi tạo app. Bước Connect to GitHub bị auto-review chặn vì chưa có chấp thuận rõ phạm vi quyền; đang chờ xác nhận. Chưa upload mã/bảng nguồn bài hoặc triển khai lên dịch vụ mới.

**Cập nhật E81 cùng ngày:** người dùng đã xác nhận kết nối và đưa gói vào repo riêng tư. Đã tạo [khanhnguyenpham/Sigma-M3-App](https://github.com/khanhnguyenpham/Sigma-M3-App), kiểm nhãn Private trong browser và push nhánh `main`, commit `a70ad2bf1b86d0e346d4e46d1ffd8a43f663fb23`. Có30tệp:29tệp đã duyệt và `.gitattributes` giữ nguyên byte release qua Git Windows/Linux. Mọi Git blob dữ liệu và manifest khớp hash được duyệt. Gói bổ sung cấu hình Git nằm local ở `outputs/hosting/sigma_source_20261018_git2/`; gói cũ giữ nguyên.

Kết nối ban đầu chỉ đọc public repo. Linked accounts của Streamlit xác nhận chưa có private access; GitHub hiển thị yêu cầu quyền **đọc và ghi toàn bộ repo public/private**, không giới hạn riêng Sigma-M3-App. Chưa bấm Authorize cho phạm vi bổ sung này; đã gửi câu hỏi xác nhận cụ thể. Form chưa khởi động build nên chưa có URL mới. Không đổi repo sang Public để giải quyết lỗi truy cập. Connector GitHub trả404 với repo mới do scope riêng của connector; browser xác minh repo và Git push/remote SHA thành công bằng kết nối Git sẵn có được người dùng cho phép.

## Gói đã chuẩn bị và kiểm tra local

Gói nằm trong `outputs/hosting/sigma_source_20261018/`, **không phải demo tự sinh**. Nó chứa ứng dụng Python dùng chung 7 màn hình M3, 11 bảng tổng hợp và manifest/receipt dẫn xuất từ hai run đã đối soát. Gói không có CSV gốc, ID đơn/khách, event ID hoặc credential. Các bảng tổng hợp vẫn là dữ liệu riêng của bài; cần chốt quyền đưa lên GitHub/Streamlit, không coi việc bỏ ID là tự động được công khai.

- Forecast: `sigma_aggregate_30d_20261016`, summary SHA `8d47a36e71c1d37fd7f55dd3bbd20ea8d2e3132b7912a1d3f27b303b23168d16`.
- M3: `sigma_m3_30d_20261016_precision_v2`, summary SHA `7086d711dfc7239adb972d2caa4bb2aac68857c338f2f42add543c385c7557ef`.
- Release manifest SHA: `629347f1224ee42e569bd1e1171b37d874ac5336b076a4b361dbc59b8c7009ec`.
- 29 tệp cần thiết, 31.500.751 byte, chưa tính hồ sơ review/QA local. Danh sách/hash từng tệp trong `package-review.json`. Không đưa hai `local-*-check.json` vào source triển khai.

Ứng dụng giữ dữ liệu/metric nguyên: tổng30 nguồn bài 9/10, mean11,786316%; China Mobile20,333443%. Tồn/nhập là mô phỏng; R05 ngày/R07/T14 còn mở. Việc chuyển hosting không chứng minh bài đạt 100%.

## Chức năng và giới hạn

Chạy Python phía server; bộ lọc tuyến/SKU/loại, tổng7/30, kịch bản, phân tích lượng bán/doanh thu, giải thích ROP/IP/Q, tải CSV, replay cảnh báo và lịch D+7 đều dùng chung mã UI sản phẩm. Bản đóng gói không cần truy cập CSV gốc để mở dashboard.

Bản này phục vụ một **release kết quả đã tính trước**. Chưa có huấn luyện/nhập dữ liệu mới/job nền trên cloud, chưa có quy trình đặt hàng thật. Giao diện đã nói rõ job local07:00 không chạy trên host này. Nếu người dùng cần vận hành cập nhật liên tục thì còn phải triển khai riêng dịch vụ nhận dữ liệu, lưu trữ, worker và kiểm thử vận hành; không được gọi gói hiện tại là hoàn thành toàn bộ sản phẩm.

## Cách mở bản đã chuẩn bị

Tại root project, dùng Python trong `.venv`, chọn prefix mới khi tạo lại:

```powershell
.venv/Scripts/python.exe -m sigma.deployment.portable --destination outputs/hosting/sigma_source_new
```

Vào thư mục gói trên máy có dependencies:

```powershell
python -m streamlit run streamlit_app.py
```

`SIGMA_RELEASE_DIR` có thể chỉ thư mục `release`; `SIGMA_RELEASE_SHA256` có thể ghim SHA manifest đã duyệt. Runtime kiểm hash mọi bảng, schema/số dòng và nhãn nguồn trước render; sửa bảng mà không khớp manifest bị chặn. Đây là kiểm integrity của gói, không phải chữ ký chống người có quyền sửa cả mã/manifest.

## Đường triển khai dự kiến

[Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) cho chọn repo/nhánh/entrypoint và subdomain trên `streamlit.app`. `sigma-inventory.streamlit.app` chỉ là **ví dụ tên**, chưa đặt và chưa xác minh còn trống. Tên miền riêng cũng có thể gắn vào Site hiện tại sau khi người dùng có hostname và cấu hình DNS; không tự mua hoặc đăng ký một tên miền.

Sau khi có xác nhận kết nối và payload: kiểm màn hình GitHub/phạm vi OAuth, dùng repo riêng tư cho gói, chỉ gửi allowlist đã duyệt, cấu hình quyền xem app theo yêu cầu rồi deploy đúng source. Không cấp thêm quyền không được phép. Quyền private của repo không tự làm app private; cần kiểm quyền xem riêng. Chưa chốt audience cho bản nguồn bài.

Theo [tài liệu chia sẻ Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app), app mới từ repo private mặc định private; cần kiểm lại thực tế sau khi deploy. [Quyền private repository](https://docs.streamlit.io/deploy/streamlit-community-cloud/status) của dịch vụ dùng OAuth `repo`, rộng hơn một repo. Luồng hiện tại đang dừng đúng màn hình quyền này, chưa có xác nhận phạm vi bổ sung.

Lần triển khai cloud đầu cần kiểm Python/dependencies trên Linux, bộ nhớ/tốc độ, load tất cả bảng, 13 kịch bản, tải CSV, URL và audience. Chỉ nhận có URL mới khi deployment thực thành công. Không dùng URL chuyển hướng/rút gọn để giả là đã thay nền tảng.

## Kiểm tra đã thực chạy

351 tests đạt; 19 tests export/portable/presentation liên quan đạt. AppTest chạy ngay từ thư mục gói độc lập không có raw: 7 tab/9 bảng/0 exception; 13 kịch bản + lọc Japan + cửa sổ7 đạt. Các bảng timeline được đối soát số nguyên/float với metric của cả13 kịch bản trước đóng gói. File allowlist/hash và header không định danh đã kiểm. Chưa kiểm môi trường Linux/cloud hoặc tài khoản GitHub kết nối.

[Mã tạo gói](../sigma/deployment/portable.py) · [Runtime](../sigma/deployment/runtime.py) · [Ứng dụng](../sigma/deployment/app.py) · [Kiểm thử](../tests/test_portable_release.py) · [Hồ sơ gói local](../outputs/hosting/sigma_source_20261018/package-review.json) · [QA tương tác local](../outputs/hosting/sigma_source_20261018/local-interaction-check.json).

Link `.chatgpt.site` cũ vẫn là demo, chưa bị đổi/xóa hoặc thay bằng nguồn bài. Chưa cập nhật nội dung hay audience của Site cũ trong lượt này.
