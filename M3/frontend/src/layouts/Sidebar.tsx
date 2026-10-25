import { PAGES } from "../config/navigation";
import { Icon } from "../components/ui/Icon";

import { type AppContextState } from "../hooks/useAppContext";

export function Sidebar({ app }: { app: AppContextState }) {
  const { page, navigate } = app;
  return (
    <aside className="sidebar" id="primary-navigation">
      <a
        className="brand"
        href="#overview"
        onClick={(e) => {
          e.preventDefault();
          navigate("overview");
        }}
      >
        <span className="brand-symbol">
          <Icon name="box" size={23} />
        </span>
        <div>
          <strong>
            sigma<span>.</span>
          </strong>
          <small>Kho SIM & gói data</small>
        </div>
      </a>
      <div className="nav-label">QUẢN LÝ KHO</div>
      <nav aria-label="Điều hướng chính">
        {PAGES.slice(0, 5).map(([id, icon, name]) => (
          <button
            key={id}
            title={name}
            className={page === id ? "selected" : ""}
            aria-current={page === id ? "page" : undefined}
            onClick={() => navigate(id)}
          >
            <Icon name={icon} />
            <span>{name}</span>
            {page === id && <i />}
          </button>
        ))}
      </nav>
      <div className="nav-label settings-label">THIẾT LẬP</div>
      <nav aria-label="Thiết lập">
        <button
          className={page === "configuration" ? "selected" : ""}
          aria-current={page === "configuration" ? "page" : undefined}
          onClick={() => navigate("configuration")}
        >
          <Icon name="settings" />
          <span>Cấu hình</span>
        </button>
      </nav>
      <div className="side-note">
        <div className="workspace-icon">
          <Icon name="box" />
        </div>
        <div>
          <strong>SIGMA · SIM & Data</strong>
          <span>
            <i className="live-dot" /> Môi trường mô phỏng
          </span>
        </div>
      </div>
    </aside>
  );
}
