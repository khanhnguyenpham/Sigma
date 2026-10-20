import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { CLOUD, initCloud } from "./api/cloud";
if (CLOUD) await initCloud();
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
