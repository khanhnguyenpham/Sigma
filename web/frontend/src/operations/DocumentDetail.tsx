import { Dialog } from "../components/ui/Dialog";
import { Table } from "../components/ui/Table";
import { State } from "../components/ui/State";
import { useResource } from "../hooks/useResource";
import { DOCUMENT_KIND, localTime, qty, type StockDocument } from "./types";

export function DocumentDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const result = useResource<StockDocument>(`/operations/documents/${id}`), document = result.data;
  return <Dialog title={document?.number ?? "Chi tiết chứng từ"} onClose={onClose} className="operations-form-dialog wide"><div className="operations-form-fields">
    <State loading={result.loading} error={result.error} />{document && !result.error && <><dl className="ops-detail-grid"><div><dt>Loại phiếu</dt><dd>{DOCUMENT_KIND[document.kind]}</dd></div><div><dt>Ngày nghiệp vụ</dt><dd>{document.occurred_on}</dd></div><div><dt>Phiếu đối chiếu</dt><dd>{document.external_ref}</dd></div><div><dt>Ghi sổ lúc</dt><dd>{localTime(document.created_at)}</dd></div></dl>
      <p>Lý do: {document.reason || "Không có"}</p><Table rows={document.lines} columns={[{ key: "sku", label: "Sản phẩm" }, { key: "warehouse", label: "Kho" }, { key: "quantity_delta", label: "Thay đổi tồn", render: qty }, { key: "balance_after", label: "Tồn sau phiếu", render: qty }]} />
      <p className="caption">Chứng từ đã ghi sổ. Nếu phát hiện sai lệch, kiểm kê và ghi phiếu điều chỉnh có lý do để giữ đầy đủ lịch sử.</p>
    </>}
  </div></Dialog>;
}
