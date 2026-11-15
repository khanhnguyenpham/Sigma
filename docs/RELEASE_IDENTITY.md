# Nhận diện release và tương thích kết quả cũ

Image bất biến có thể đặt `M3_RELEASE_VERSION` bằng full commit SHA40ký tự hoặc semantic version như `v1.2.3`. Khi đó `core.hashes.code_digest()` dùng token ổn định từ release đã đóng gói, **không đọc lại toàn bộ source hoặc gọi Git ở mỗi job/request**. CI truyền đúng GitHub SHA vào build argument; Compose nhận `SIGMA_RELEASE_VERSION` khi người vận hành build release.

Các cột/manifest legacy `code_sha256` vẫn lưu token64ký tự cho khả năng đọc dữ liệu cũ; đây là token của **release reference**, không được diễn giải thành SHA của từng tệp mã. Snapshot/manifest mới có `runtime_code_reference={mode:immutable-release-v1,version:...}`; FE chỉ đọc mode/version hợp lệ, không chuyển JSON tùy ý hoặc credential. Thay release khi có source mới; không gắn cùng version cho hai image khác nhau.

Không có biến release thì tiếp tục chế độ source-file guard cũ, dành cho local còn chỉnh sửa. Đây là lựa chọn có chủ ý: sửa file sau enqueue vẫn phải bị phát hiện. Code/manifest của run lịch sử không viết lại; không xóa checksum dữ liệu/artifact/selection hoặc password hash/token digest của auth để làm mất khả năng kiểm tra. Những checksum audit này khác với quét source ở runtime.

Kiểm riêng: release không cần source/Git, đổi version đổi token, local sửa source đổi token, version sai bị chặn không echo đầu vào, snapshot chỉ xuất hai trường allowlist. Full hồi quy và CI image cần đạt trước khi dùng release mới. Benchmark riêng cho kiểm identity giữ local; không coi tiết kiệm thời gian đọc source là tăng tốc mô hình hoặc giảm dung lượng dữ liệu.
