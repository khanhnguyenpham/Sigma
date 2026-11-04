import { useDialogFocus } from "../../hooks/useDialogFocus";
export function HelpDialog({ onClose }: { onClose: () => void }) {
  useDialogFocus(true, onClose);
  return (
    <div className="modal-shade">
      <section
        className="modal help-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-title"
      >
        <button className="close" aria-label="Đóng hướng dẫn" onClick={onClose}>
          ×
        </button>
        <span className="eyebrow">TRỢ GIÚP</span>
        <h2 id="help-title">Sử dụng SIGMA</h2>
        <p className="caption">
          Quản lý nhu cầu và tồn kho SIM/gói data theo quốc gia, nhà mạng và mặt
          hàng.
        </p>
        <h3>Bắt đầu một kế hoạch</h3>
        <ol>
          <li>
            Mở Kịch bản để thiết lập, lưu phiên bản rồi chạy. Theo dõi tiến độ và xem kết quả ngay trên trang đó.
          </li>
          <li>
            Chọn phương án và ngày kế hoạch ở thanh bộ lọc khi xem các trang kết quả. Dự báo hai khối 7 ngày được phân bổ thành 14 ngày để tính tồn; ngày nghiệp vụ theo UTC.
          </li>
          <li>
            Mở Tồn kho, chọn kho theo tên thành phố rồi chọn sản phẩm để xem
            thông tin và cấu hình nhập hàng. Nút Chỉnh sửa kho nằm ngay trong trang kho.
          </li>
          <li>
            Trong Nhập hàng, rà Cần bổ sung, Đang về và Lịch sử. Đề xuất chưa
            phải đơn gửi nhà cung cấp.
          </li>
          <li>
            Mở Cảnh báo để xem thời điểm cạn dự kiến và đường tồn 14 ngày.
          </li>
        </ol>
        <h3>Đọc các chỉ số tồn</h3>
        <dl className="help-glossary">
          <dt>Tồn hiện có</dt>
          <dd>
            Số lượng đóng sổ tại ngày chọn. Hàng đang về chưa được cộng vào đây.
          </dd>
          <dt>Ngưỡng nhập (ROP)</dt>
          <dd>
            Với kế hoạch mới, ROP = max(nhu cầu dự báo 7 ngày + SS, ngưỡng nhập tối thiểu đã cấu hình).
            SS tính theo số ngày tồn an toàn. Hệ thống xét nhập khi tồn hiện có nhỏ hơn ROP; kế hoạch cũ giữ công thức đã chốt.
          </dd>
          <dt>Vị thế tồn (IP)</dt>
          <dd>
            Tồn hiện có cộng hàng đã đặt, dùng tính lượng cần đặt. IP đủ có thể
            làm lượng đề xuất bằng 0 dù tồn dưới ngưỡng.
          </dd>
          <dt>Lượng nhập mỗi lần</dt>
          <dd>
            Khi cần bổ sung, mỗi lô dùng đúng lượng đã cấu hình cho mặt hàng,
            không tự tăng theo dự báo.
            Ngày nhận dự kiến bằng ngày đặt cộng 7 ngày.
          </dd>
        </dl>
        <h3>Thử thay đổi</h3>
        <p>
          Mở Sản phẩm, chọn mặt hàng và chỉnh lượng nhập mỗi lần, số ngày tồn an toàn hoặc ngưỡng nhập.
          Chọn kho nhận mặc định tại sản phẩm. Lưu cấu hình rồi mở Kịch bản để tạo kế hoạch theo ngày hiệu lực.
        </p>

        <h3>Tải dữ liệu và xử lý lỗi</h3>
        <p>
          CSV chứa toàn bộ kết quả theo bộ lọc. Bấm Xuất CSV để tải kết quả.
          Nếu mất kết nối, bấm Làm mới dữ liệu; thao tác này không thay đổi
          phương án đã lưu. Chưa có actual được
          hiển thị trống, không phải 0.
        </p>
        <button className="primary" onClick={onClose}>
          Đã hiểu
        </button>
      </section>
    </div>
  );
}
