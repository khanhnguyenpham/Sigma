import { useEffect, useId, useRef, type ReactNode } from "react";

/** Native modal keeps the background inert; explicit Tab cycling keeps focus in the workspace. */
export function Dialog({ title, onClose, children, className = "", busy = false }: {
  title: string; onClose: () => void; children: ReactNode; className?: string; busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const node = ref.current!;
    const previous = document.activeElement as HTMLElement | null;
    node.showModal();
    return () => { node.close(); if (previous?.isConnected) previous.focus(); };
  }, []);
  return <dialog ref={ref} className={`workspace-dialog ${className}`} aria-labelledby={titleId} aria-busy={busy}
    onKeyDown={(event) => {
      if (event.key !== "Tab") return;
      const node = event.currentTarget;
      const targets = Array.from(node.querySelectorAll<HTMLElement>("button,input,select,textarea,a[href],summary,[tabindex]"))
        .filter((target) => target.tabIndex >= 0 && !target.matches(":disabled") && target.getClientRects().length > 0);
      const first = targets[0], last = targets.at(-1);
      if (!first) { event.preventDefault(); return; }
      if (event.shiftKey && (document.activeElement === first || !node.contains(document.activeElement))) {
        event.preventDefault(); last?.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !node.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    }}
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose(); }}>
    <header className="dialog-heading"><h2 id={titleId}>{title}</h2><button type="button" onClick={onClose} autoFocus disabled={busy}>Đóng</button></header>
    {children}
  </dialog>;
}
