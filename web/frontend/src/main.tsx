import React from "react";
import "./index.css";
import "./styles/management.css";
import "./styles/operations.css";
import { createRoot } from "react-dom/client";
import App from "./App";
import { PageBoundary } from "./components/ui/PageBoundary";
import { SessionBoundary } from "./auth/SessionBoundary";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PageBoundary>
      <SessionBoundary><App /></SessionBoundary>
    </PageBoundary>
  </React.StrictMode>,
);
