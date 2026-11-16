import { NAV_GROUPS, isManagementPage } from "../config/navigation";
import { useEffect, useRef } from "react";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { Icon } from "../components/ui/Icon";

import { type AppContextState } from "../hooks/useAppContext";

export function Sidebar({ app }: { app: AppContextState }) {
  const { page, navigate, navOpen, setNavOpen } = app;
  const compact = useMediaQuery("(max-width: 1100px)");
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!compact || !navOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.querySelector<HTMLButtonElement>(".sidebar-close")?.focus();
    return () => { if (previous?.isConnected) previous.focus(); };
  }, [compact, navOpen]);
  return (
    <aside ref={ref} className="sidebar" id="primary-navigation" inert={compact && !navOpen}
      aria-hidden={compact && !navOpen ? true : undefined} role={compact && navOpen ? "dialog" : undefined}
      aria-modal={compact && navOpen ? true : undefined} aria-label={compact && navOpen ? "Điều hướng" : undefined}
      onKeyDown={(event) => {
        if (!compact || !navOpen || event.key !== "Tab") return;
        const targets = Array.from(event.currentTarget.querySelectorAll<HTMLElement>("a[href],button:not(:disabled)"))
          .filter((target) => target.getClientRects().length > 0);
        if (event.shiftKey && document.activeElement === targets[0]) { event.preventDefault(); targets.at(-1)?.focus(); }
        else if (!event.shiftKey && document.activeElement === targets.at(-1)) { event.preventDefault(); targets[0]?.focus(); }
      }}>
      {compact && <button className="icon-button sidebar-close" aria-label="Đóng menu điều hướng" onClick={() => setNavOpen(false)}><Icon name="close" size={18} /></button>}
      <a
        className="brand"
        href="#dashboard"
        onClick={(e) => {
          e.preventDefault();
          navigate("dashboard");
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
      <nav aria-label="Điều hướng chính">
        {NAV_GROUPS.map(([group, pages]) => (
          <div key={group || "home"}>
            {group && <div className="nav-label">{group}</div>}
            {pages.map(([id, icon, name]) => {
              // The single Tools entry stays selected on every forecast/scenario page.
              const selected = id === "forecast" ? !isManagementPage(page) : page === id;
              return <button key={id} title={name} className={selected ? "selected" : ""}
                aria-current={selected ? "page" : undefined} onClick={() => navigate(id)}>
                <Icon name={icon} />
                <span>{name}</span>
                {selected && <i />}
              </button>;
            })}
          </div>
        ))}
      </nav>
      <div className="side-note">
        <div className="workspace-icon">
          <Icon name="box" />
        </div>
        <div>
          <strong>SIGMA · SIM & Data</strong>
          <span>
            <i className="live-dot" /> {isManagementPage(page) ? "Sổ kho vận hành" : "Công cụ mô phỏng"}
          </span>
        </div>
      </div>
    </aside>
  );
}
