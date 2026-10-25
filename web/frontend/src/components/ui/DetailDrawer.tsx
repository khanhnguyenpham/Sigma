import { Icon } from "./Icon";
import { useDialogFocus } from "../../hooks/useDialogFocus";

export function DetailDrawer({
  title,
  eyebrow = "Chi tiết mặt hàng",
  children,
  onClose,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  useDialogFocus(true, onClose);
  return (
    <div className="drawer-shade" onClick={onClose}>
      <section
        className="detail-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <div>
            <span className="eyebrow">{eyebrow}</span>
            <h2>{title}</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Đóng chi tiết"
            onClick={onClose}
          >
            <Icon name="close" />
          </button>
        </header>
        <div className="drawer-body">{children}</div>
      </section>
    </div>
  );
}
