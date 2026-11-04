# Hướng dẫn thao tác và trình bày demo SIGMA

Soạn ngày 04/11/2026, phục vụ luyện demo thứ Sáu 06/11/2026. Hướng dẫn gồm launcher, so sánh14ngày và kết quả C00; [bàn giao và cổng publish GitHub](development.md#handoff-demo-ui-publish) ghi phạm vi kiểm và trạng thái phát hành. Demo đã nâng migration0009 và cập nhật đồng bộ API/worker/giao diện; dùng tại [demo HTTPS công khai](https://that-katrina-olympus-situated.trycloudflare.com/#scenarios) hoặc [localhost](http://127.0.0.1:8041/#scenarios). Người dùng đã xác nhận công khai qua Quick Tunnel; cần giữ máy và process chạy, URL đổi khi mở tunnel mới. Lấy connection.json làm nguồn URL hiện hành. [Bàn giao HTTPS và giới hạn kiểm](development.md#handoff-demo-https-public).

Đã dọn3lượt thử cũ, demo còn6lượt: một nguồn, một dự báo, kế hoạch tồn mới31/10, kế hoạch nhập, kiểm tra cảnh báo và một lượt lỗi còn liên kết thử lại. Đầu trang Kịch bản có kết quả C00 toàn kỳ54,02% đã chạy lại/kiểm chứng. [Bản phục hồi trước dọn và phạm vi giữ lại](development.md#handoff-demo-run-cleanup).

Backup mới và diễn tập migration0009 trên bản sao đã hoàn tất trước cutover. Bản backup0008 vẫn giữ nguyên để phục hồi khi cần. [Bản backup và kết quả diễn tập](development.md#handoff-demo-0009-rehearsal).

## 1. Câu giới thiệu và cách hiểu tổng thể

Bạn có thể mở đầu:

> SIGMA hỗ trợ dự báo nhu cầu và lập kế hoạch tồn kho cho SIM/eSIM theo thị trường, nhà mạng và sản phẩm. Từ dữ liệu đơn hàng đã có, hệ thống dự báo nhu cầu, mô phỏng tồn và lô nhập, đề xuất bổ sung và cảnh báo nguy cơ thiếu hàng. Người dùng có thể thay đổi giả định để so sánh các phương án.

Luồng chính: **Nguồn đơn hàng → Dự báo nhu cầu → Kịch bản → Lượt chạy → Tồn kho / Nhập hàng / Cảnh báo / Dự kiến bán / CSV**.

- Đơn hàng là dữ liệu nguồn đã cung cấp; dữ liệu demo được dẫn xuất và ẩn danh. Tồn đầu, lô nhập, lead time và các thay đổi cung cấp trong mô phỏng là giả định được khai báo.
- Đơn vị chính là số lượng sản phẩm. Không diễn giải dữ liệu tiền đã đưa về0 trong bộ demo thành doanh thu thực tế.
- Một tuyến dự báo được xác định bởi thị trường/quốc gia và nhà mạng. Kho nhận hàng có thể khác kho danh mục/tuyến nguồn; đổi kho nhận không đổi tuyến dự báo.
- Một kịch bản chứa giả định. Một lượt chạy là một lần xử lý bằng giả định và dữ liệu cụ thể. Có thể giữ nhiều lượt để xem lại.
- Lưu cấu hình chưa tạo ra phép tính mới. Cần tạo lượt chạy mới để có kết quả sử dụng cấu hình mới.

## 2. Những khái niệm phải đọc đúng

| Trên web | Hiểu và giải thích |
|---|---|
| Phương án / lượt chạy | Bộ kết quả của một lần xử lý. Kiểm đúng loại công việc, trạng thái, mã và ngày trước khi diễn giải. |
| Mốc chốt / origin | Ngày đứng tại đó để lập kế hoạch; D là mốc này. D+1 là ngày tiếp theo. |
| Ngày số liệu / Ngày kế hoạch | Kế hoạch tồn kho một mốc hiển thị Ngày số liệu cố định theo phương án. Với replay nhiều ngày, Ngày kế hoạch là ngày đang đọc số liệu trong khoảng đã ghi nhận. |
| Ngày thao tác / ngày ghi nhận | Ngày biết một thay đổi cung cấp trong mô phỏng. Khác với ngày thay đổi bắt đầu có hiệu lực. |
| Tồn hiện có | Số lượng tồn tại ngày đang xem; chưa cộng hàng chưa về. Đây là tồn mô phỏng trong project. |
| Hàng đang về | Lô đã được ghi nhận đặt nhưng chưa đến ngày nhận dự kiến. |
| Vị thế tồn IP | Tồn hiện có cộng hàng đang về. Hệ thống xét lượng này khi tính cần đặt thêm. |
| ROP | Ngưỡng nhập cố định của sản phẩm. Tồn nhỏ hơn ROP tạo tín hiệu dưới ngưỡng; bằng ROP chưa thỏa điều kiện nhỏ hơn. |
| Lượng nhập mỗi lần | Lượng cố định dùng cho mỗi lần cần bổ sung theo policy, còn phải xét quyền nhập và ràng buộc nhà mạng. |
| SS / tồn an toàn | Tính theo số ngày tồn an toàn, nhu cầu dự báo trung bình và hệ số safety. Bản hiện tại dùng ROP cố định, không cộng SS vào ROP. |
| ETA | Ngày dự kiến nhận lô, bằng ngày đặt cộng7ngày theo giả định hiện tại. |
| L7 / R1 / H14 | Lead time7ngày; xét bổ sung hằng ngày; nhìn trước14ngày. |
| Tồn được bán / tồn bị chặn | Phần có quyền bán và phần bị nhà mạng hạn chế bán. Tổng tồn không tự biến mất khi quyền bán bị chặn. |
| Actual | Nhãn lượng bán nguồn đã quan sát trong kỳ đối chiếu. Chưa có actual được để thiếu/trống, không thay bằng0. |
| Phiên bản đã chốt | Thiết lập và dữ liệu được giữ cho lượt chạy. Sửa cấu hình hiện tại không sửa ngược kết quả cũ. |

Ví dụ minh họa: ROP100, tồn60, không có hàng đang về và lượng nhập mỗi lần50 thì có thể đề xuất50 khi các điều kiện khác cho phép. Nếu tồn60 và đang về60, IP là120; nếu đã đủ mức mục tiêu thì lượng cần đặt có thể bằng0 dù tồn hiện có vẫn dưới ROP. Khi cần đặt, hệ thống dùng lượng cố định; không tự nâng lượng này chỉ vì phần thiếu lớn hơn. Ràng buộc cung cấp có thể chặn đề xuất.

## 3. Bản đồ các trang

| Trang | Câu hỏi nó trả lời |
|---|---|
| Tổng quan | Hôm nay trong phương án này cần chú ý điều gì? |
| Tồn kho | Kho nào có bao nhiêu hàng, sản phẩm nào thấp hơn ngưỡng? |
| Sản phẩm | Mỗi sản phẩm được cấu hình nhập, kho nhận và lịch cung cấp ra sao? |
| Dự báo nhu cầu | Nhu cầu đầu vào là bao nhiêu; từ tồn đang có dự kiến bán được bao nhiêu? |
| Nhập hàng | Cần bổ sung gì, lô nào đang về, lô nào đã ghi nhận? |
| Cảnh báo | Sản phẩm nào sắp xuống ngưỡng hoặc cạn, vào thời điểm nào? |
| Kịch bản | Thiết lập giả định, chạy và xem lại kết quả của từng lần xử lý. |

### Tổng quan

Chọn một phương án tồn/nhập/cảnh báo đã hoàn tất và ngày có dữ liệu. Đọc4thẻ: **Tồn hiện có**, **Cần bổ sung**, **Lô hàng đang về**, **Cảnh báo cần xử lý**. Cần bổ sung là số mặt hàng; lượng đơn vị đề xuất nằm ở chú thích, không phải cùng một đại lượng.

Với Kế hoạch tồn kho một mốc, ô **Ngày số liệu UTC** được khóa theo phương án, ví dụ31/10/2025. Đây là số liệu điều hành tại mốc đó; để xem14ngày tiếp theo bấm **Xem Dự kiến bán14ngày**. Link cũ có ngày khác được đưa về mốc đúng. Muốn xem số liệu điều hành tại mốc khác, chọn phương án tương ứng hoặc tạo lượt mới; đổi ngày không tự tính lại. [Bàn giao thay đổi](development.md#handoff-snapshot-date).

Đọc bảng Mặt hàng cần bổ sung, biểu đồ Tồn kho theo tuyến và Lịch hàng đang về. Nhấn một mặt hàng hoặc Xem tất cả để đi sâu. Trong bản mới, lịch sử chạy và thử lại nằm tại Kịch bản.

Lời trình bày: “Trang này tóm tắt phạm vi đang chọn. Em có thể đi từ số tổng sang sản phẩm cần xử lý để biết nguyên nhân và lượng đề xuất.”

### Tồn kho

Mở danh sách kho, lọc/tìm kho rồi chọn một kho. Tên chính là địa danh; quốc gia và nhà mạng là thông tin riêng. Với run mới có kho nhận mặc định, số tồn và lô được đọc theo kho nhận đã chốt.

Trong kho, lọc nhà mạng, loại sản phẩm, SKU hoặc trạng thái. Đọc Tồn hiện có, Đang về, Ngưỡng nhập, Cần đặt; nếu có hạn chế mua bán thì đọc thêm Tồn được bán/Tồn bị chặn. Nhấn dòng sản phẩm mở cấu hình. Chỉnh sửa kho dùng để chỉnh thông tin kho theo form hiện có, không phải thao tác điều chuyển tồn. Xuất CSV lấy đủ phạm vi lọc, không chỉ trang bảng đang thấy.

Với kế hoạch tồn tại một mốc, muốn xem14ngày tương lai thì mở Dự kiến bán/Cảnh báo. Không suy luận ngày tương lai không có sổ tồn thành tồn0.

### Sản phẩm: cấu hình và kho nhận

Tìm sản phẩm bằng SKU/kho/nhà mạng/loại/trạng thái. Một SKU có thể cần phân biệt thêm loại sản phẩm và kho/tuyến nguồn; không chọn chỉ bằng chuỗi SKU nếu có nhiều dòng.

Nhấn **Cấu hình**. Các ô cần hiểu:

| Ô | Dùng để làm gì |
|---|---|
| Kho nhận hàng mặc định | Đích của tồn/lô trong lượt chạy mới. Chưa cấu hình riêng thì kế thừa kho của sản phẩm. Lưu bằng nút Lưu kho nhận. |
| Ngưỡng nhập cố định (ROP) | Ngưỡng để xét sản phẩm đang dưới mức cần chú ý. |
| Lượng nhập mỗi lần | Lượng cố định khi quyết định bổ sung thỏa điều kiện. |
| Số ngày tồn an toàn | Tham số tính SS; không tự làm ROP cố định tăng lên. |
| Số ngày nhìn trước cảnh báo xuống ROP | Phạm vi1–14ngày để cảnh báo dự kiến xuống ngưỡng. |
| Áp dụng từ ngày | Thời điểm policy mới bắt đầu có hiệu lực. |

**Lưu kho nhận và Lưu cấu hình sản phẩm là hai thao tác riêng.** Đổi kho nhận không chuyển ngay tồn hoặc đổi đích lô của run cũ. Lượt mới tự chốt mặc định từng sản phẩm; không phải chọn lại kho nhận ở Kịch bản.

Điểm đặc biệt khi luyện: dữ liệu mô phỏng nằm trong2024–2025, còn form sửa policy hiện đặt ngày hiệu lực mới từ ngày hiện tại hoặc muộn hơn phiên bản trước. Vì vậy lưu policy hiệu lực2026 không làm run mốc2025 đổi lượng nhập. Có thể trình diễn việc lưu/version riêng; để so sánh ROP trên lịch sử, dùng Điều chỉnh riêng mặt hàng trong kịch bản. Kịch bản không cho đổi lượng nhập mỗi lần hoặc kho nhận. Không sửa ngày tùy ý để cố làm kết quả khớp mong muốn.

### Lịch cung cấp: hai nghiệp vụ khác nhau

Vào **Sản phẩm → Lịch cung cấp** tại đúng dòng. Chọn Ngày thao tác UTC trong thời gian mô phỏng.

| Nghiệp vụ | Ảnh hưởng |
|---|---|
| Ngừng nhập nội bộ | Dừng đặt thêm cho sản phẩm tại kho đang quản lý; vẫn được bán phần tồn có quyền bán và nhận lô đã đặt. Bản mới cho ngừng cùng ngày ghi nhận. |
| Nhà mạng ngừng cung cấp | Chặn nhập và bán mới theo sản phẩm/thị trường/kho được khai báo. Không tự cắt dịch vụ khách đã mua hoặc xóa lô đã đặt. |

Ngừng nhập nội bộ: nhấn Đặt lịch ngừng nhập, nhập ngày ghi nhận/ngày hiệu lực/lý do, bấm Xem tác động rồi mới lưu. Lịch tương lai có thể hủy; khi đã ngừng có thao tác mở nhập lại theo trạng thái hợp lệ.

Nhà mạng: nhấn Đặt lịch ngừng cung cấp, kiểm thông tin điền sẵn, chọn phạm vi thị trường/kho và điền ngày, lý do, nguồn khai báo/giả định. Bấm Xem phạm vi và tác động, kiểm số sản phẩm/kho rồi Lưu thông báo. Có lịch sử; thông báo chưa hiệu lực có thể hủy, trường hợp đã ngừng có thao tác ghi nhận cung cấp trở lại khi hợp lệ.

Gỡ một thông báo không tự gỡ ngừng nhập nội bộ hoặc thông báo nhà mạng khác. Sau khi lưu, tạo kế hoạch mới để xem tác động. Trong demo lịch sử, ngày ghi nhận/hiệu lực phải phù hợp mốc đang mô phỏng; không dùng năm2026 rồi kỳ vọng có tác động ở tháng10/2025.

### Dự báo nhu cầu và dự kiến bán

**So sánh theo ngày ngay trong kịch bản:** mở **Kịch bản → chọn lượt đã hoàn tất → So sánh dự báo / thực tế**. Hoặc mở trang **Dự báo nhu cầu**, khối so sánh nằm phía trên phần dự kiến bán theo tồn.

Trong kết quả kịch bản, khối so sánh nằm ởtab**So sánh dự báo / thực tế**. Tab**Dự kiến bán** đã được bỏ; phần dự phóng theo tồn vẫn có ở trangDựbáonhucầu riêng.

**Kết quả C00 để trình bày:** mở **Kịch bản**, khối **Đánh giá C00 — hồi cứu toàn kỳ** nằm đầu trang. Phép kiểm đã chạy lại từ đầu vào/dự báo/chính sách frozen và đối chiếu verifier đường tồn cùng hai scorer: **450/833 = 54,02%**, Precision **80,89%**, Recall **79,95%**, sai lệch ngày cạn trung bình **4,01 ngày** trên666 đợt có cảnh báo. Kỳ chấm29/10–31/12/2025,920 mặt hàng, tự bổ sung hàng và28 ngày khởi tạo. Một mặt hàng có thể cạn nhiều đợt sau khi nhập lại. Bấm **Cách tính và nguồn kết quả C00** để giải thích hoặc **Tải kết quả C00** lấy JSON tổng hợp có mã đối chiếu. Đây là đánh giá nghiên cứu đã chốt, không tự đổi theo phiên bản kịch bản/bộ lọc và không phải tập kiểm định chưa từng xem.

Câu demo gợi ý: “Trong phép hồi cứu C00 toàn kỳ,450 trên833 đợt cạn được báo trước ít nhất7ngày, tương đương54,02%. Precision cảnh báo là80,89%; đây là hai chỉ số khác nhau.”

**Tỷ lệ cảnh báo của từng lượt14ngày:** mở **Kịch bản → lượt Kiểm tra cảnh báo hoàn tất → Tóm tắt**. Thẻ Báo sớm≥7ngày tính số sự kiện cạn được cảnh báo khi còn ít nhất7ngày chia tổng sự kiện cạn đủđiềukiện; mẫu số gồm cả báo muộn/bỏsót, không đổi theo bộlọc. Lượt demo kỳ01–14/10/2025 đạt**32,5% (150/461)**; đây là phép kiểm không đặt hàng mới trong cửa sổ14ngày, khác phép hồi cứu C00 toàn kỳ phía trên. Không dùng54,02% thay tỷ lệ của lượt này. Precision68,5% vàRecall65,5% đo khía cạnh khác nên hiển thị riêng. Mẫu số0ghiChưaxácđịnh, không tự gọi0% hoặc100%.

Cardbáosớm nằm ngaydưới hàngtab khi chọn**Tóm tắt**. Nếu đang xemKếhoạchtồnkho, hệthốngcóthểhiện kếtquảđãđánhgiá của replaycompletecùngphiênbảnscenario vàcùngnguồn/dựbáocha, kèmnhãnnguồnvàkỳhồicứu. Ví dụstockc02ngày31/10hiệnkếtquảliênquanc145kỳ01–14/10, **không phải tỷlệ đo riêngcho31/10**. Nút **Mở lượt Kiểm tra cảnh báo này** dẫnđếnlượtnguồn. Khi chưacólượtphùhợp thìghi chưađánhgiá.

Chọn **Ngày đánh giá UTC** từ các mốc đã lưu. Ví dụ chọn31/10/2025 thì so sánh lượng dự báo và lượng bán nguồn thực tế từ01/11đến14/11; đổi sang01/11thì xem02/11đến15/11. Đọc3thẻ Dự báo14ngày, Bán thực tế14ngày và Chênh lệch=dựbáo−thựctế, rồi xem biểu đồ/bảng theo tuyến. Tổng gồm toàn phạmvi; biểu đồ chỉ minh họa12tuyếnđầu. CSV là các dòng tuần/ngày nền của đúng mốc, có thể cộng lại để đối chiếu.

Ngày đánh giá chỉ đổi cửa sổ so sánh, không đổi ngày tồn đã chốt hoặc tạo run. Mốc31/12trong demo chưa có thực tế14ngày tiếp theo nên hiện **Chưa đủ thực tế**; phần thiếu không tính0, còn bán thực tế0vẫnhiện0. Phạm vi theo tuyến nguồn/SKU/loại, không áp bộ lọc kho nhận/quyền mua bán; dự kiến bán theo tồn là phần mô phỏng khác. Ngày đánh giá trong phiên xem trở về mặc định khi rời khối/tải lại, không lưu thành phiên bản kịch bản.

Nếu chọn lượt forecast đã hoàn tất, trang đọc nhu cầu đầu vào theo **Tổng7ngày**, Tuần1 D+1…D+7 / Tuần2 D+8…D+14, hoặc **Phân bổ theo ngày**. Tổng tuần thuộc tuyến; lọc SKU/loại dùng ở phần phân bổ ngày. Số ngày được phân bổ từ dự báo tổng tuần, không nên mô tả là14mô hình riêng cho từng ngày.

Nếu chọn kế hoạch tồn/nhập/cảnh báo, phần chính là **Dự kiến bán theo tồn/ràng buộc**: nhu cầu có thể lớn hơn lượng bán được vì thiếu hàng hoặc bị chặn bán. Mở “Nhu cầu dự báo và chất lượng lịch sử” để xem đầu vào dự báo.

Mở Chất lượng dự báo lịch sử khi được hỏi: MAPE là sai số phần trăm và chỉ chấm actual dương; MAE là sai số tuyệt đối trung bình theo số lượng; WAPE là tổng sai số tuyệt đối trên tổng actual; Bias biểu thị xu hướng lệch; độ phủ/cặp chấm cho biết phạm vi đủ nhãn. Bảng là metric các cửa sổ test lịch sử, không chỉ ngày đang vẽ. Đây là chẩn đoán H14; ứng dụng đã gỡ Tổng30. Không tuyên bố các bảng này chứng minh đã đạt tiêu chí nghiên cứu Tổng30 hoặc mọi tuyến đều đạt20%.

### Nhập hàng

Chọn đúng phương án và ngày. Có3danh sách:

- **Cần bổ sung:** lượng đề xuất; đọc tồn, đang về, ROP, cần đặt và ngày nhận nếu đặt. Khi có hạn chế, xem Q trước/sau giới hạn và lý do.
- **Đang về:** lô đã được ghi nhận đặt và đang chờ ETA tại ngày xem; chưa cộng vào tồn hiện có.
- **Lịch sử lô nhập:** các lô đã được ghi nhận trong phạm vi phù hợp của kế hoạch; xem ngày đặt, ETA, lượng và trạng thái.

Nhấn dòng để xem chi tiết và xuất CSV theo bộ lọc. Với stock_projection, đề xuất tại mốc không tự trở thành đơn đã đặt/đang về; cần phân biệt với lô đầu kỳ đã khai báo và lô mô phỏng trong policy replay. Các nút này không gửi đơn mua đến nhà cung cấp thật.

### Cảnh báo

Lọc theo loại tín hiệu và trạng thái, nhấn dòng để xem đường tồn dự kiến và các yếu tố ảnh hưởng.

| Tín hiệu | Câu giải thích |
|---|---|
| Dưới ngưỡng nhập | Tồn tại ngày đang xem đã nhỏ hơn ROP. Có thể chưa cần đặt thêm nếu hàng đang về đã đủ. |
| Dự kiến xuống ROP | Hiện chưa xuống, nhưng đường tồn dự kiến sẽ xuống trong số ngày nhìn trước được cấu hình. |
| Nguy cơ cạn | Nhìn vào thời điểm tồn dự kiến hết; dưới7ngày cần xử lý sớm, từ7ngày trở lên có thời gian chuẩn bị hơn. |
| Chưa cạn trong14ngày | Chưa thấy cạn trong phạm vi quan sát; không khẳng định sẽ không cạn về sau. |

Xuống ROP và hết hàng là hai mốc khác nhau. Một sản phẩm có thể có nhiều tín hiệu; thẻ tổng số mặt hàng không cộng trùng các dòng cảnh báo.

Phần đánh giá lịch sử chỉ hiện khi run có metric thích hợp, thường dùng alert replay. Precision: trong các cảnh báo được chấm, tỷ lệ đúng; Recall: trong các sự kiện thực sự thuộc phạm vi chấm, tỷ lệ phát hiện được. Tỷ lệ báo sớm≥7ngày khác hai chỉ số này. Các ca chưa đủ nhãn hoặc bị hạn chế bán có scope/exclusions riêng; giảm số bán do chặn không tự được coi là cải thiện dự báo. Lọc bảng không tự thay mẫu số metric toàn lượt.

## 4. Thao tác trang Kịch bản từ đầu đến cuối

1. Mở Kịch bản hoặc Tạo phương án. Chọn một phiên bản đã lưu hoặc Tạo kịch bản mới.
2. Nhập Tên kịch bản dễ nhận biết, ví dụ `Demo cơ sở`; mã chỉ gồm chữ thường không dấu, số, `_` hoặc `-`, ví dụ `demo_co_so`.
3. Chọn Tồn đầu3/7/14ngày phủ. Đây là giả định khởi tạo tồn: lượng bán trung bình28ngày đã biết nhân số ngày phủ rồi làm tròn lên; không phải số tồn doanh nghiệp cung cấp.
4. Hệ số safety dùng cùng số ngày tồn an toàn để tính SS. Do dùng ROP cố định, tăng riêng hệ số này không đảm bảo lượng nhập tăng. Để minh họa thay đổi rõ, so sánh ngày phủ hoặc ROP override đã luyện trước.
5. Nếu cần điều chỉnh riêng: chọn Kho danh mục để tìm item, bấm Điều chỉnh mặt hàng, chọn đúng item và nhập ROP/số ngày tồn an toàn/số ngày nhìn trước. Ô trống kế thừa policy sản phẩm. Kho này chỉ giúp tìm item, không ghi đè kho nhận.
6. Nếu có lô đã biết tại mốc: thêm Lô đang về, kiểm đúng item, ngày đặt, số lượng. ETA tự bằng ngày đặt+7; ngày đặt không sau mốc chốt. Ví dụ mốc31/10/2025: đặt28/10, ETA04/11, lượng50. Để danh sách trống nghĩa không khai báo lô đầu kỳ.
7. Bấm **Lưu thiết lập**. Kiểm tên/phiên bản vừa trả về. Lưu không tự chạy; sửa phiên bản có sẵn rồi lưu tạo phiên bản mới.
8. Chọn loại công việc. Với kế hoạch tồn/nhập/cảnh báo, chọn forecast cha đã hoàn tất, mốc chốt và kỳ chạy nếu có. Chọn mốc có dữ liệu forecast phù hợp;31/10/2025 là ví dụ, phải đối chiếu forecast thực tế được chọn.
9. Bấm **Chạy kịch bản** sau khi đã lưu bản nháp. Lượt mới tự dùng kho nhận mặc định của từng sản phẩm tại lúc nhận job và giữ nó cho run đó.
10. Theo dõi queued/đang xếp hàng → running/đang xử lý → complete/đã hoàn tất. Có thể rời trang/reload rồi mở lại đúng lượt; không tự gửi lại job.
11. Khi complete, xem kết quả ngay tại trang: Tóm tắt, Tồn kho, Nhập hàng, Cảnh báo, Dự kiến bán. Đổi bộ lọc để đọc số liệu và xuất CSV. Cấu hình đã chốt có mục xem riêng.
12. Mở Các lượt đã chạy của phiên bản này để xem lại. Khi sửa bản nháp, kết quả đang xem vẫn thuộc lượt cũ; sau khi lưu/chạy mới cần chọn đúng phiên bản/lượt để so sánh.

### Chọn đúng loại công việc

| Lựa chọn trên web | Dùng khi | Cần chuẩn bị |
|---|---|---|
| Kế hoạch tồn kho | Xem một mốc và dự kiến tồn/bán14ngày; phù hợp chạy trực tiếp trong demo ngắn. | Nguồn + forecast hoàn tất + scenario đã lưu. |
| Kế hoạch nhập hàng | Mô phỏng tồn, nhận hàng và quyết định bổ sung qua một giai đoạn. | Nguồn/forecast đủ kỳ, scenario và khoảng thời gian. |
| Kiểm tra cảnh báo | Đánh giá cảnh báo qua các cửa sổ lịch sử có nhãn đối chiếu. | Nguồn/forecast đủ kỳ, scenario và khoảng thời gian. |
| Nhập nguồn | Đọc bộ nguồn đã đăng ký trên server, tạo dữ liệu cho các bước sau. | Bộ nguồn hợp lệ đã đặt sẵn; đây không phải màn upload CSV tùy ý. |
| Tạo dự báo | Tạo dự báo đầu vào từ nguồn hoàn tất. | Nguồn hoàn tất; có thể là công việc tốn thời gian. |

Với hai loại replay, ngày bắt đầu kỳ phải là mốc chốt+1ngày và kỳ phải nằm trong phạm vi dữ liệu hỗ trợ. Ví dụ mốc30/09, kỳ từ01/10. Mỗi công việc có bước gửi riêng, không có thao tác ngầm chạy toàn bộ pipeline.

Trên sân khấu nên dùng nguồn/forecast hoàn tất đã chuẩn bị, chạy một Kế hoạch tồn kho ngắn. Không đặt toàn bộ buổi demo phụ thuộc vào việc vừa tạo forecast/replay dài. Chọn source/forecast làm phương án ở trang Tồn kho sẽ không có bộ kết quả tồn tương ứng.

## 5. Bài demo12–15phút và câu dẫn

| Thời lượng | Thao tác | Lời giải thích chính |
|---|---|---|
| 0–1phút | Giới thiệu bài toán và dữ liệu. | “Từ đơn hàng, hệ thống dự báo và hỗ trợ quyết định tồn/nhập. Các số tồn và lô ở đây là mô phỏng theo giả định.” |
| 1–3phút | Chọn kế hoạch hoàn tất, ngày hợp lệ; mở Tổng quan rồi một kho. | “Em nhìn được mặt hàng nào cần xử lý, số tồn, lượng đang về và đề xuất cụ thể.” |
| 3–5phút | Từ sản phẩm trong kho mở Cấu hình; giải thích ROP, lượng cố định, kho nhận. | “Kho nhận được cấu hình ở sản phẩm; kịch bản sẽ tự dùng. Policy có ngày hiệu lực riêng.” |
| 5–8phút | Mở Kịch bản, lưu một phiên bản, chọn forecast có sẵn và chạy Kế hoạch tồn kho. | “Lưu và chạy là hai thao tác riêng. Mỗi run giữ cấu hình và dữ liệu để tra cứu lại.” |
| 8–10phút | Khi complete, mở Tồn kho/ Nhập hàng/ Cảnh báo ngay tại trang. | “Bảng này dùng đúng run vừa tạo, không tự chuyển sang kết quả của lần khác.” |
| 10–11phút | Nhấn một cảnh báo, xem đường tồn và ngày xuống ROP/ngày cạn. | “Hệ thống phân biệt dưới ngưỡng và hết hàng để ưu tiên xử lý.” |
| 11–13phút | Mở Lịch cung cấp, trình bày preview ngừng nhập hoặc ngừng nhà mạng đã luyện. | “Ngừng nhập nội bộ vẫn bán tồn; nhà mạng dừng sản phẩm có thể chặn cả mua và bán mới trong phạm vi khai báo.” |
| 13–15phút | Xuất CSV, mở lại lượt cũ; nếu được hỏi thì mở metric lịch sử. | “Kết quả có thể tải và đối chiếu. Lượt cũ vẫn giữ nguyên để so sánh.” |

Nếu chỉ có10phút, dành phần lifecycle cho câu hỏi; tập trung chuỗi Tổng quan→sản phẩm→Kịch bản→kết quả→CSV. Không cần mở mọi bảng metric hoặc đọc mọi cột kỹ thuật.

## 6. Chuẩn bị các tình huống có thể giải thích được

- **A — Cơ sở:** cover7ngày, cấu hình được kế thừa, không có lô đầu kỳ. Lưu kết quả hoàn tất làm mốc.
- **B — Tồn đầu thấp:** cùng nguồn/forecast/mốc với A, đổi cover3ngày. Quan sát số liệu thực của một item đã chọn trước; không hứa mọi SKU đều tăng cảnh báo vì còn làm tròn và các ràng buộc khác.
- **C — Hàng đang về:** cùng mốc, khai báo một lô có ngày đặt trước mốc và ETA sau mốc. Chỉ ra IP/hàng đang về có thể làm lượng cần đặt giảm, trong khi tồn hiện có chưa cộng lô.
- **D — Ngừng cung cấp:** chuẩn bị một thông báo có ngày/phạm vi phù hợp, preview rồi tạo run mới. Dùng kết quả đã luyện để giải thích quyền nhập/bán, tồn bị chặn và lịch sử.

Không cần chạy cả4tình huống trực tiếp. Nên có A/B hoặc C đã complete trước buổi demo, chỉ chạy thêm một lượt ngắn tại chỗ. Các tên và số minh họa trong tài liệu không phải lựa chọn/run đã được tạo trên demo.

## 7. Những câu hỏi thường gặp

**Tại sao lưu cấu hình mà bảng chưa đổi?** Bảng thuộc run đã chốt; kiểm ngày hiệu lực, tạo run mới và chọn đúng run mới. Làm mới dữ liệu chỉ đọc lại, không tính lại.

**Tại sao dưới ROP mà cần đặt0?** Kiểm IP/hàng đang về và quyền nhập, hạn chế nhà mạng, ETA/lô. Tín hiệu dưới ngưỡng và lượng đề xuất là hai kết quả cần đọc cùng nhau.

**Dự báo bán100 thì chắc chắn bán100?** Đó là nhu cầu ước lượng. Dự kiến bán theo tồn còn chịu giới hạn lượng hàng và quyền bán; phần không phục vụ được có cột riêng.

**Đổi kho có chuyển hàng ngay không?** Lưu mặc định chỉ ảnh hưởng run mới. Run/lô đã chốt và định danh nguồn được giữ.

**Có thể mua hàng/gửi đơn thật từ web không?** Chức năng ở đây là đề xuất và mô phỏng lô nhập, chưa gửi đơn đến nhà cung cấp thật.

**Tại sao không có Tổng30?** Ứng dụng hiện tập trung vận hành H14. Không dùng bảng tuần/ngày trên web để khẳng định tiêu chí Tổng30 đã đạt; R05 vẫn là phần cần đối chiếu riêng.

**Run failed có mất dữ liệu cũ không?** Giữ lượt cũ. Nút Thử lại với cấu hình hiện tại tạo lượt khác có liên kết; mặc định hiện tại có thể khác lượt lỗi. Không sửa trạng thái hoặc lấy số partial làm kết quả hoàn tất.

**Bảng trống có phải dữ liệu hỏng?** Kiểm loại run/trạng thái/ngày/kho/SKU và các bộ lọc. Mở source/forecast ở màn tồn hoặc chọn ngày không có dữ liệu cũng có thể trống. Null/chưa actual không phải0.

## 8. Chuẩn bị và xử lý tình huống buổi demo

Điểm khởi động đã đặt ở `src/start_demo.py`. Từ thư mục project chạy `.\.venv-m3\Scripts\python.exe src/start_demo.py start`, giữ terminal; dùng `status` để xem và `stop` ở terminal khác để dừng. Chỉ mở URL khi status báo active=true/ready. Cần hoàn tất cập nhật demo theo [quy trình launcher](../web/backend/configs/DEMO_RUNTIME.md#src-demo-launcher) trước; không bỏ qua kiểm tra mã đã duyệt.

Trước buổi demo cần cập nhật bản mới lên demo, mở API/worker/PostgreSQL/tunnel, kiểm đúng URL hiện hành và thử từ một thiết bị khác. Quick Tunnel chỉ phục vụ khi máy và các tiến trình còn chạy; URL có thể đổi khi mở tunnel mới.

Chọn trước một kho/SKU, ghi mốc/kỳ và tên các lượt hoàn tất. Kiểm forecast cha đủ dữ liệu, policy có lượng nhập phù hợp, lô đầu kỳ có ngày hợp lệ. Luyện toàn bài ít nhất một lần trên bản sẽ trình chiếu. Chuẩn bị CSV/ảnh và các lượt đã complete để vẫn giải thích được nếu mạng gián đoạn; không trình bày ảnh dự phòng như một lượt vừa chạy.

| Hiện tượng | Cách xử lý |
|---|---|
| Nút chạy bị khóa | Kiểm đã lưu scenario, còn bản nháp, đang gửi job hay thiếu/lỗi tải forecast/nguồn. |
| Thiếu dự báo/không đủ lịch sử | Chọn forecast/mốc/kỳ đã chuẩn bị; không tùy ý chọn ngày hôm nay với dữ liệu2025. |
| Chờ hàng đợi | Giữ mã run, chờ worker; không bấm tạo nhiều lượt hoặc nhập nguồn/dự báo lại liên tục. |
| Giới hạn lượt/hàng đợi429 | Đọc thông báo và thời gian chờ, chuyển sang lượt hoàn tất dự phòng. |
| Cấu hình đã thay đổi409 | Tải lại cấu hình và kiểm phiên bản trước khi lưu lại; không khẳng định lần ghi lỗi đã thành công. |
| Lưu chưa rõ kết quả/mất mạng | Đọc lại danh sách/phiên bản trước khi gửi thêm; tránh tạo trùng. |
| Run complete nhưng bảng tải lỗi | Thử tải lại phần dữ liệu, không tạo lại run chỉ vì lỗi đọc. |
| Link không vào được | Kiểm máy/process/tunnel và URL hiện hành; không coi link Quick Tunnel là hosting luôn online khi tắt máy. |

Ba câu cần nhớ khi trình bày: **mỗi kết quả gắn với một lượt chạy**, **tồn và nhập được mô phỏng theo giả định**, **thay cấu hình thì chạy lượt mới để so sánh**.
