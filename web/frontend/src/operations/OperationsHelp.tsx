import { Dialog } from "../components/ui/Dialog";

export function OperationsHelp({ onClose }: { onClose: () => void }) {
  return <Dialog title="Sử dụng sổ kho" onClose={onClose} className="operations-form-dialog"><div className="operations-form-fields">
    <section><h3>1. Khai báo ban đầu</h3><p>Thêm kho tại Kho hàng, thêm SKU tại Sản phẩm. Đặt thời gian nhập mặc định tại Nhà cung cấp. Nếu kho đã có hàng, dùng Kiểm kê / tồn đầu và nhập số lượng đếm thực tế.</p></section>
    <section><h3>2. Nhập hàng</h3><p>Tạo đơn nhập, chọn nhà cung cấp, kho và số lượng. Lưu nháp rồi xác nhận đặt hàng. Khi hàng về, mở đơn và chọn Nhận hàng, nhập mã phiếu giao cùng số lượng thực nhận. Có thể nhận nhiều lần đến khi đủ.</p></section>
    <section><h3>3. Xuất và đối chiếu</h3><p>Tại Tồn kho, chọn Xuất kho hoặc Kiểm kê cho sản phẩm. Kiểm kê nhập số đếm được, kể cả 0; hệ thống tự tính chênh lệch. Mọi thay đổi cần mã phiếu và lý do.</p></section>
    <section><h3>4. Tra cứu lịch sử</h3><p>Chứng từ ghi số lượng tăng, giảm và tồn sau mỗi phiếu. Lịch sử thao tác ghi người thực hiện. Phiếu đã ghi sổ không sửa trực tiếp; dùng kiểm kê để điều chỉnh có lý do.</p></section>
    <p className="caption">Sổ kho vận hành dùng ngày Việt Nam (UTC+7). Các trang Dự báo & kế hoạch sử dụng kết quả mô phỏng riêng; chưa tự lấy số dư sổ kho để tính lại kế hoạch.</p>
  </div></Dialog>;
}
