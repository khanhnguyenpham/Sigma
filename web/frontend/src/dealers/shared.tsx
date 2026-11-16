import type { ReactNode } from "react";
import { Dialog } from "../components/ui/Dialog";
import { State } from "../components/ui/State";
import { Table } from "../components/ui/Table";
import { WriteError } from "../operations/WriteError";
import { useResource } from "../hooks/useResource";
import { localTime, qty } from "../operations/types";

export const REQUEST_STATUS: Record<string, string> = {
  submitted: "Chờ duyệt", approved: "Đã duyệt, chờ xuất", rejected: "Từ chối", cancelled: "Đã hủy", issued: "Đã xuất, chờ nhận", received: "Đã nhận",
};

export interface DealerRequest {
  id: number; number: string; status: string; version: number; note: string; reject_reason: string | null;
  dealer_code: string; dealer_name: string; created_at: string; received_at: string | null;
  lines: { item_id: number; sku: string; name: string; quantity: number }[];
}

export const statusBadge = (value: unknown) => <span className={`ops-status dealer-${value}`}>{REQUEST_STATUS[String(value)] ?? String(value)}</span>;

/** Shared request view; each side passes only the actions its role may take. */
export function RequestDetail({ path, onClose, busy, error, actions }: {
  path: string; onClose: () => void; busy: boolean; error?: Error; actions: (request: DealerRequest) => ReactNode;
}) {
  const detail = useResource<DealerRequest>(path);
  const request = detail.data;
  return <Dialog title={request?.number ?? "Chi tiết yêu cầu"} onClose={onClose} busy={busy} className="operations-form-dialog wide">
    <div className="operations-form-fields">
      <State loading={detail.loading} error={detail.error} />
      <WriteError error={error} />
      {request && <>
        <p>{request.dealer_name} ({request.dealer_code}) · {statusBadge(request.status)} · tạo lúc {localTime(request.created_at)}</p>
        {request.note && <p className="caption">Ghi chú: {request.note}</p>}
        {request.reject_reason && <p className="notice error">Lý do từ chối: {request.reject_reason}</p>}
        <Table rows={request.lines} label="Sản phẩm yêu cầu" columns={[{ key: "sku", label: "SKU" }, { key: "name", label: "Sản phẩm" }, { key: "quantity", label: "Số lượng", render: qty }]} />
      </>}
    </div>
    {/* Block a second approve/issue/receive while one is being sent. */}
    {request && <fieldset className="dialog-form-actions" disabled={busy}>{actions(request)}
      {busy && <span className="caption" role="status">Đang xử lý…</span>}</fieldset>}
  </Dialog>;
}
