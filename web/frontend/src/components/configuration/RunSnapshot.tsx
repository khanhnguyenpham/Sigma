import { useState } from "react";
import type { Run } from "../../types/api";
import { Icon } from "../ui/Icon";
import { SnapshotDialog } from "./SnapshotDialog";

export function RunSnapshot({ run, title = "Thiết lập đã chốt của lượt chạy" }: { run: Run; title?: string }) {
  const [open, setOpen] = useState(false);
  return <><button type="button" className="snapshot-trigger" onClick={() => setOpen(true)} aria-haspopup="dialog">
    <Icon name="settings" size={15} />{title}
  </button>{open && <SnapshotDialog key={run.id} run={run} title={title} onClose={() => setOpen(false)} />}</>;
}
