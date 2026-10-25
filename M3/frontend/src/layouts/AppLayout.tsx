import { Suspense } from "react";
import { State } from "../components/ui/State";
import { HelpDialog } from "../components/dialogs/HelpDialog";
import { PageBoundary } from "../components/ui/PageBoundary";
import { RunDialog } from "../components/dialogs/RunDialog";

import { type AppContextState } from "../hooks/useAppContext";

import type { ReactNode } from "react";

import { Sidebar } from "./Sidebar";

import { Header } from "./Header";

import { ContextFilters } from "./ContextFilters";

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
    dialog,
    setDialog,
    runs,
    ctx,
    setCtx,
    runsResource,
    run,
    selectedResource,
    setRefresh,
    navigate,
  } = app;
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
      <main>
        <Header app={app} />
        <div className="workspace" id="workspace-content" tabIndex={-1}>
          {page !== "configuration" && <ContextFilters app={app} />}
          <State
            loading={runsResource.loading && !runsResource.data}
            error={runsResource.error}
          />
          {ctx.runId &&
          !run &&
          (runsResource.loading || selectedResource.loading) ? (
            <State loading />
          ) : ctx.runId && runsResource.data && !run ? (
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
              L7 · R1 · H14 <span className="footer-dot">·</span> Ngày nghiệp vụ
              UTC
            </span>
          </footer>
        </div>
      </main>
      {help && <HelpDialog onClose={() => setHelp(false)} />}
      {dialog && (
        <RunDialog
          runs={runs}
          onClose={() => setDialog(false)}
          onCreated={(id) => {
            setDialog(false);
            setCtx((c) => ({ ...c, runId: id, origin: "" }));
            setRefresh((v) => v + 1);
            navigate("overview");
          }}
        />
      )}
    </div>
  );
}
