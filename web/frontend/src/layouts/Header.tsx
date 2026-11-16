import { isManagementPage, pageTitle } from "../config/navigation";
import { Icon } from "../components/ui/Icon";
import { AccountMenu } from "../auth/SessionBoundary";

import { type AppContextState } from "../hooks/useAppContext";

export function Header({ app }: { app: AppContextState }) {
  const {
    page,
    navOpen,
    setNavOpen,
    busyRun,
    setHelp,
    openScenarios,
  } = app;
  const [section, selectedTitle] = pageTitle(page);
  const tool = !isManagementPage(page);
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
        <span className="breadcrumb-root">{section}</span>
        <Icon name="chevron" size={14} />
        <strong>{selectedTitle}</strong>
      </div>
      <div className="top-status">
        <AccountMenu />
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
        {tool && busyRun && (
          <button
            className="task-indicator"
            onClick={() => {
              openScenarios(busyRun.id);
            }}
          >
            <i className="spinner" />
            Đang xử lý
          </button>
        )}
        {tool && <span className="environment-pill">
          <Icon name="info" size={14} /> {"Dữ liệu mô phỏng"}
        </span>}
        {tool && page !== "scenarios" && <button className="primary header-create" aria-label="Tạo phương án" onClick={() => openScenarios()}>
          <Icon name="plus" size={17} />
          <span>Tạo phương án</span>
        </button>}
      </div>
    </header>
  );
}
