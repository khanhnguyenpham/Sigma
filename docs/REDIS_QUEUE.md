# Hàng đợi Redis và trạng thái PostgreSQL

`M3_QUEUE_DRIVER=postgres` giữ cách chạy local cũ. `redis` dùng Redis Streams làm transport, còn các row `runs.status=queued` đã commit là **durable outbox/ý định công việc**. Không tạo Redis message ngay trong request API và không để Redis làm nơi duy nhất giữ trạng thái. Không thêm một bảng outbox trùng thông tin Run.

## Luồng chạy

1. API commit run queued như trước, cùng snapshot/request key đã kiểm. Redis lỗi không làm mất run đã lưu.
2. Worker giữ advisory lock PostgreSQL cho một worker hoạt động. Dispatcher đọc queued bằng row lock/SKIP LOCKED, XADD mã run/schema version rồi mới ghi dấu publish vào metadata transport của run. Crash ở giữa có thể phát lặp, không xóa ý định queued.
3. Consumer dùng XREADGROUP; PG chuyển queued→running bằng row lock theo đúng runID. Message lặp của run running/complete không gọi tính toán lần hai.
4. Chỉ ACK sau khi DB đã ở trạng thái complete/failed/invalidated; sau ACK xóa message đã xử lý của nhóm worker duy nhất. Redis là vận chuyển, lịch sử nằm trong PG/artifact.
5. XAUTOCLAIM thu hồi message pending sau60giây, giữ cursor khi quét. Vì một worker hoạt động, không thu hồi job dài để tính song song. Restart đánh dấu running cũ failed/interrupted như hợp đồng trước; người dùng retry thành run mới, không tự refit cùng run cũ.
6. Run complete trước ACK: message được thu hồi và ACK, không tính lại. Redis mất message/stream: queued còn trong PG, dấu publish quá60giây được phát lại. Không âm thầm đổi sang worker polling PG khi Redis lỗi.

Worker kiểm lại running trước bước ghi kết quả và trước commit hoàn tất; không biến run đã interrupted thành complete. Exception không ghi đè trạng thái terminal đã có. Advisory-lock connection dùng AUTOCOMMIT, tránh giữ transaction idle suốt đời worker gây cản vacuum. Đây không phải cơ chế chạy nhiều worker; concurrency vẫn1.

## Cấu hình

File env riêng:

```text
M3_QUEUE_DRIVER=redis
M3_REDIS_URL=redis://:REPLACE_LOCALLY@127.0.0.1:6379/0
M3_QUEUE_NAMESPACE=sigma:m3:v1
```

Không dùng URL mẫu làm credential thật. Redis8/persistence AOF được đóng gói trong Compose, không mở port Redis ra host. Mật khẩu Redis thứ ba phải độc lập mật khẩu app/admin PostgreSQL. Mỗi môi trường có instance/DB/namespace riêng; không chia stream của hai dataset.

Queue status chỉ admin qua `/api/v1/operations/queue-status`, không trả URL hoặc mật khẩu. Trang Kịch bản báo Redis chưa sẵn sàng và vẫn cho đọc kết quả đã lưu. Trạng thái này kiểm transport, không tự chứng minh worker đã bật; với Compose phải bật profile `jobs` để xử lý hàng chờ.

## Kiểm và giới hạn

Local không có Redis server: test outbox lỗi, gửi trùng, interrupted và worker guard chạy trên PG synthetic; test Redis thật được skip có lý do. CI backend có service Redis thật, bắt buộc hai ca XADD/XREADGROUP/ACK và reclaim sau commit-trước-ACK; nếu thiếu env trên CI thì fail, không skip. Compose CI kiểm thêm đăng nhập API, Redis có mật khẩu và role app không superuser. Chỉ nhận các cổng này qua khi có kết quả của đúng commit.

Giới hạn: không quảng cáo exactly-once transport, không tự chạy lại job ML bị ngắt, không xử lý đa-worker/đa-nhóm consumer. Giữ guard source/artifact/fingerprint hiện có. Publisher dùng metadata transport trong result_summary chỉ khi queued; progress nghiệp vụ thay khi running. Chưa có benchmark tải lớn hoặc chính sách lưu hàng đợi vô hạn. Không dùng Redis để lưu raw hay customerID.

Nguồn kỹ thuật: [XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/), [XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/), [XACK](https://redis.io/docs/latest/commands/xack/), [redis-py8.1.0](https://pypi.org/project/redis/).
