import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { CLOUD, initCloud } from "./api/cloud";
import { PageBoundary } from "./components/PageBoundary";
const root = createRoot(document.getElementById("root")!);
if (CLOUD)
  root.render(
    <main className="bootstrap-error" role="status">
      <h1>Đang kết nối SIGMA…</h1>
      <p>
        Đang mở dữ liệu kế hoạch. Lần truy cập đầu có thể lâu hơn khi máy chủ
        vừa khởi động.
      </p>
    </main>,
  );
try {
  if (CLOUD) await initCloud();
  root.render(
    <React.StrictMode>
      <PageBoundary>
        <App />
      </PageBoundary>
    </React.StrictMode>,
  );
} catch {
  root.render(
    <main className="bootstrap-error" role="alert">
      <h1>Chưa kết nối được SIGMA</h1>
      <p>
        Máy chủ có thể đang khởi động hoặc kết nối vừa gián đoạn. Kiểm tra mạng
        rồi thử lại.
      </p>
      <button className="primary" onClick={() => window.location.reload()}>
        Tải lại trang
      </button>
    </main>,
  );
}
