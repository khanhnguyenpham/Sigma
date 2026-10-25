import React from "react";
import "./index.css";
import { createRoot } from "react-dom/client";
import App from "./App";
import { PageBoundary } from "./components/ui/PageBoundary";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PageBoundary>
      <App />
    </PageBoundary>
  </React.StrictMode>,
);
