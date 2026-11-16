import { Suspense } from "react";
import { State } from "../components/ui/State";
import { HelpDialog } from "../components/dialogs/HelpDialog";
import { PageBoundary } from "../components/ui/PageBoundary";

import { type AppContextState } from "../hooks/useAppContext";

import type { ReactNode } from "react";

import { Sidebar } from "./Sidebar";

import { Header } from "./Header";

import { ContextFilters } from "./ContextFilters";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { OperationsHelp } from "../operations/OperationsHelp";
import { TOOL_PAGES, isManagementPage } from "../config/navigation";

export function AppLayout({
  app,
  children: node,
}: {
  app: AppContextState;
  children: ReactNode;
}) {
  const {
    navOpen,
    setNavOpen,
    page,
    help,
    setHelp,
    ctx,
    runsResource,
    run,
    selectedResource,
  } = app;
  const management = isManagementPage(page);
  // Pages without the run selector: the real ledger, plus tool pages that manage their own context.
  const managementPage = management || ["scenarios", "configuration", "products", "product"].includes(page);
  const toolTab = page === "product" ? "products" : page;
  const compact = useMediaQuery("(max-width: 1100px)");
  return (
    <div className={"shell " + (navOpen ? "nav-open" : "")}>
      <a
        className="skip-link"
        href="#workspace-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("workspace-content")?.focus();
        }}
      >
        Bỏ qua menu, tới nội dung
      </a>
      {navOpen && (
        <button
          className="nav-scrim"
          aria-label="Đóng menu"
          onClick={() => setNavOpen(false)}
        />
      )}
      <Sidebar app={app} />
      <main inert={compact && navOpen}>
        <Header app={app} />
        <div className="workspace" id="workspace-content" tabIndex={-1}>
          {!management && <>
            <nav className="ops-tabs tool-tabs" aria-label="Công cụ dự báo">{TOOL_PAGES.map(([id, name]) =>
              <button key={id} aria-current={toolTab === id ? "page" : undefined} onClick={() => app.navigate(id)}>{name}</button>)}</nav>
            <label className="ops-mobile-tabs">Công cụ<select value={toolTab} onChange={(event) => app.navigate(event.target.value)}>
              {TOOL_PAGES.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
          </>}
          {!managementPage && <ContextFilters app={app} />}
          {!management && <State
            loading={runsResource.loading && !runsResource.data}
            error={runsResource.error}
          />}
          {!managementPage && ctx.runId &&
          !run &&
          (runsResource.loading || selectedResource.loading) ? (
            <State loading />
          ) : !managementPage && ctx.runId && runsResource.data && !run ? (
            <div className="notice error" role="alert">
              Không tìm thấy phương án trong liên kết. Hãy chọn lại phương án;
              dữ liệu không được tự đổi sang kế hoạch khác.
            </div>
          ) : (
            <PageBoundary key={page}>
              <Suspense fallback={<State loading />}>{node}</Suspense>
            </PageBoundary>
          )}
          <footer>
            <span>
              <button className="text-button" onClick={() => setHelp(true)}>
                Hướng dẫn sử dụng
              </button>{" "}
              · SIGMA · Quản lý nhu cầu & tồn kho
              {""}
            </span>
            <span>
              {management ? "Sổ kho · Ngày nghiệp vụ Việt Nam (UTC+7)" : "Công cụ dự báo · Lead time theo nhà cung cấp · R1 · H14 · Ngày dữ liệu UTC"}
            </span>
          </footer>
        </div>
      </main>
      {help && (management ? <OperationsHelp onClose={() => setHelp(false)} /> : <HelpDialog onClose={() => setHelp(false)} />)}
    </div>
  );
}
