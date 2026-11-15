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
  const managementPage = ["operations", "scenarios", "configuration", "products", "product"].includes(page);
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
          {!managementPage && <ContextFilters app={app} />}
          {page !== "operations" && <State
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
              {page === "operations" ? "Sổ kho · Ngày nghiệp vụ Việt Nam (UTC+7)" : "L7 · R1 · H14 · Ngày dữ liệu dự báo UTC"}
            </span>
          </footer>
        </div>
      </main>
      {help && (page === "operations" ? <OperationsHelp onClose={() => setHelp(false)} /> : <HelpDialog onClose={() => setHelp(false)} />)}
    </div>
  );
}
