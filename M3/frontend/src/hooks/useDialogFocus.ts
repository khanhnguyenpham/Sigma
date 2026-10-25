import { useEffect, useRef } from "react";

export function useDialogFocus(open: boolean, onClose: () => void) {
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = Array.from(
      document.querySelectorAll<HTMLElement>('[role="dialog"]'),
    ).at(-1);
    const targets = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input:not([type="hidden"]):not(:disabled),select:not(:disabled),textarea,a[href]',
        ) ?? [],
      ).filter((el) => el.getClientRects().length > 0);
    targets()[0]?.focus();
    const key = (event: KeyboardEvent) => {
      if (
        dialog !==
        Array.from(
          document.querySelectorAll<HTMLElement>('[role="dialog"]'),
        ).at(-1)
      )
        return;
      if (event.key === "Escape") {
        event.preventDefault();
        close.current();
      }
      if (event.key === "Tab") {
        const list = targets(),
          first = list[0],
          last = list.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [open]);
}
