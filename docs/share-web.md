# Dashboard SIGMA chia sẻ cho nhóm

Đã xuất bản ngày 18/10/2026: **[Mở dashboard SIGMA](https://sigma-demand-inventory.cuddly-grebe-5666.chatgpt.site)**. Sites xác nhận deployment `succeeded`, quyền xem `public` (revision 2). Bạn bè mở URL trên máy tính hoặc điện thoại; máy đang chạy project không cần bật để phục vụ trang này.

Đây là bản trình diễn **hoàn toàn dùng dữ liệu tự sinh**, gồm 10 tuyến minh họa, 20 SKU và 13 kịch bản. Nó không dùng CSV gốc và không thay kết quả đánh giá nguồn bài. Bản nguồn bài vẫn ở local: tổng 30 đạt 9/10, MAPE trung bình 11,786316%; China Mobile 20,333443%, R05 ngày/R07/T14 còn mở.

## Dùng khi trình diễn

1. **Tổng quan:** chọn quốc gia/nhà mạng, đọc nhu cầu 30 ngày và các SKU cần xem xét.
2. **Dự báo:** đổi tổng 7/30 ngày. Chọn ngày chốt 30/11/2025 để xem kỳ đã có actual; 31/12/2025 để thấy kỳ tương lai chưa có actual.
3. **Kho hàng:** chọn mặt hàng, đọc tồn/ROP/IP/Q và xuất phiếu đề xuất CSV. Phiếu không tạo đơn nhập thật.
4. **Kịch bản:** thử đối tác giao 50%, giao trễ, không nhận hàng hoặc lượng bán giảm; so sánh tồn/thiếu với cơ sở.
5. **Cảnh báo:** đọc riêng cảnh báo hiện tại và replay H14; ca cạn trước ngày 7 vẫn ở mẫu số chính.
6. **Giao khách:** xem lịch D+7, tách với lead time nhập kho.
7. **Kiểm chứng:** giải thích nguồn tự sinh, cách chia tập, giới hạn và hash hai run demo.

Nút **Sao chép liên kết** giữ bộ lọc trong URL. Nút **Hướng dẫn** mở kịch bản trình diễn ngắn. Bộ lọc SKU áp dụng kho/cảnh báo; dự báo và biểu đồ kịch bản ghi rõ phạm vi theo tuyến.

## Phạm vi online

Trang đọc snapshot đã tính trước, có bộ lọc, biểu đồ, 13 tình huống và xuất CSV. Nó không có backend huấn luyện, cơ sở dữ liệu giao dịch, cập nhật tự động hoặc gửi đơn nhập. Mỗi CSV được gắn `generated_synthetic_demo`; đơn/khách hàng và CSV tự sinh cấp giao dịch cũng không nằm trong gói web.

MAPE demo tổng 7 là 7,870876%, tổng 30 là 4,312166%, cả hai 10/10. Đây chỉ là kiểm tra luồng trên dữ liệu chương trình tạo, **không phải bằng chứng bài đã đạt 10/10 trên nguồn được cung cấp**. Cơ sở tồn demo đáp ứng 100%; cảnh báo sớm 109/120 cũng chỉ áp dụng demo này.

## Triển khai và bằng chứng

| Hạng mục | Giá trị |
| --- | --- |
| Site | `appgprj_6ad455f724148191b279d49c11d9eb96` |
| Phiên bản | 1 |
| Source commit của Site | `668e6c93161ceb8dbbdbf40eff6c1d5b47ae9375` |
| Deployment | `appgdep_6ad45d149740819197c2c36463b4b488` |
| Gói dữ liệu web | 1.393.603 byte, SHA `baf347390798de178d240fa5085265c3c35c0f49984e27ef448f38d7170ccb35` |
| Forecast demo summary SHA | `4cfe3894d9ce5068dbdc22fcc9b22add2c23daea82a14e4ba5632892849ae644` |
| Policy demo summary SHA | `741ee325220e70f044cb6664e1291a59c19dc7f61916c8c1401b98120ad91e4a` |

Gói xuất bản có 4 tệp `index.html`, `styles.css`, `app.js`, `demo.json` và manifest hosting. Source nằm tại `sites/sigma-demand-inventory/`, được Sites quản lý bằng Git riêng và ignored ở repo SIGMA. Credential chỉ truyền qua stdin ẩn; không lưu trong source. CSV gốc, run nguồn bài, tài khoản và khóa API không xuất bản.

Lần đầu auto-review đã từ chối đồng bộ vì chưa rõ payload/đích Sites. Sau khi xem bản cụ thể, người dùng xác nhận **“Đồng ý xuất bản công khai trên Sites”**, rồi mới thực hiện đồng bộ và xuất bản. Không dùng hosting khác để vượt chặn.

Đã chạy: 344 tests đạt; 4 guard export chạy lại đạt; nguồn demo tái sinh khớp SHA; forecast/policy demo kiểm độc lập; timeline đối soát 13 kịch bản; 241 tệp được bảo vệ và hai summary nguồn bài nguyên hash. Browser kiểm 7 màn hình, 13 lựa chọn tình huống, lọc tuyến/SKU, kỳ có/thiếu actual, hướng dẫn, đặt lại và điện thoại 390 px không tràn ngang. Phiếu CSV tải thực có 2 SKU Việt Nam, tổng Q=10 khớp màn hình. Trên URL online, bộ lọc Nhật Bản/giao 50% cập nhật và không có console error.

Giới hạn kiểm tra: receipt file tải dự báo chưa được công cụ browser thu lại, không coi là đã đối chiếu file đó. Request HTTP không cookie bằng Python gặp Cloudflare 1010; browser mở được trang và Sites xác nhận quyền public, nhưng chưa có xác nhận từ một thiết bị bạn bè độc lập.

[Bằng chứng kiểm tra](../reports/share_20261018/verification.json) · [Deployment](../reports/share_20261018/deployment.json) · [Ảnh online](../reports/share_20261018/online.png) · [Ảnh điện thoại](../reports/share_20261018/mobile.png) · [Gói web dự phòng local](../reports/share_20261018/SIGMA_web_demo_review.zip). Các tệp bằng chứng/gói dự phòng vẫn local; chỉ source Site/gói web đã được phép được gửi lên Sites.

## Tái tạo demo từ mã

Tại root project, với môi trường đã cài theo README, chọn prefix **mới**:

```powershell
.venv/Scripts/python.exe -m sigma.sharing.demo --prefix sigma_share_my_demo
.venv/Scripts/python.exe -m sigma.sharing.export --config outputs/sigma_share_my_demo_bundle/product30.json --destination sites/sigma-demand-inventory/dist/demo.json
```

Lệnh thứ hai kiểm nguồn tái sinh và verification receipts trước khi xuất allowlist. Nó chưa tự xuất bản; để cập nhật Site, dùng workflow Sites với đúng Site ID, source commit và gói build tương ứng. Giữ audience theo yêu cầu người dùng; không đưa raw/run riêng vào checkout Site.
