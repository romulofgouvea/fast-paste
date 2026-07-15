import React from "react";
import ReactDOM from "react-dom/client";
import { getCurrentWindow } from "@tauri-apps/api/window";
import App from "./App";
import Settings from "./windows/Settings";
import "./index.css";
import "highlight.js/styles/atom-one-dark.css";

// Uma única SPA atende as duas janelas: o label decide o que renderizar.
const isSettings = getCurrentWindow().label === "settings";

window.addEventListener("error", (e) => {
  document.body.innerHTML = `<pre style="color:red;background:white;padding:16px;white-space:pre-wrap;font-size:14px">DIAG ERROR: ${e.message}\n${e.error?.stack ?? ""}</pre>`;
});
window.addEventListener("unhandledrejection", (e) => {
  document.body.innerHTML = `<pre style="color:red;background:white;padding:16px;white-space:pre-wrap;font-size:14px">DIAG REJECTION: ${String(e.reason)}\n${e.reason?.stack ?? ""}</pre>`;
});

try {
  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      {isSettings ? <Settings /> : <App />}
    </React.StrictMode>,
  );
} catch (err) {
  document.body.innerHTML = `<pre style="color:red;background:white;padding:16px;white-space:pre-wrap;font-size:14px">DIAG THROW: ${String(err)}\n${(err as Error)?.stack ?? ""}</pre>`;
}
