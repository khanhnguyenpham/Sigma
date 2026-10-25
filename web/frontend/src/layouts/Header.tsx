import { PAGES } from "../config/navigation";
import { Icon } from "../components/ui/Icon";

import { type AppContextState } from "../hooks/useAppContext";

export function Header({ app }: { app: AppContextState }) {
  const {
    page,
    navOpen,
    setNavOpen,
    busyRun,
    selectRun,
    navigate,
    setHelp,
    setDialog,
  } = app;
  const selectedTitle = PAGES.find((p) => p[0] === page)?.[2] ?? "Tổng quan";
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <button
          className="icon-button mobile-menu"
          aria-label="Mở menu"
          aria-expanded={navOpen}
          aria-controls="primary-navigation"
          onClick={() => setNavOpen(true)}
        >
          <Icon name="menu" />
        </button>
        <span className="breadcrumb-root">Kho SIM/data</span>
        <Icon name="chevron" size={14} />
        <strong>{selectedTitle}</strong>
      </div>
      <div className="top-status">
        <button
          className="icon-button"
          aria-label="Làm mới dữ liệu"
          title="Làm mới dữ liệu trong phiên"
          onClick={() => window.dispatchEvent(new Event("sigma:refresh"))}
        >
          <Icon name="refresh" size={17} />
        </button>
        <button
          className="icon-button help-trigger"
          aria-label="Hướng dẫn sử dụng"
          title="Hướng dẫn sử dụng"
          onClick={() => setHelp(true)}
        >
          <Icon name="info" size={17} />
        </button>
        {busyRun && (
          <button
            className="task-indicator"
            onClick={() => {
              selectRun(busyRun.id);
              navigate("overview");
            }}
          >
            <i className="spinner" />
            Đang xử lý
          </button>
        )}
        <span className="environment-pill">
          <Icon name="info" size={14} /> {"Dữ liệu mô phỏng"}
        </span>
        <button className="primary" onClick={() => setDialog(true)}>
          <Icon name="plus" size={17} />
          Tạo phương án
        </button>
      </div>
    </header>
  );
}
