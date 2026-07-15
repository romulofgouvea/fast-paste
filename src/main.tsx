import React from "react";
import ReactDOM from "react-dom/client";
import { getCurrentWindow } from "@tauri-apps/api/window";
import App from "./App";
import Settings from "./windows/Settings";
import "./index.css";
import "highlight.js/styles/atom-one-dark.css";

// Detecção do tipo de janela:
// 1º: __FPASTE_WINDOW__ injetado via initialization_script do Rust
//     (mais confiável — roda antes de qualquer JS no WebView2)
// 2º: fallback pelo label de getCurrentWindow()
declare global {
  interface Window {
    __FPASTE_WINDOW__?: string;
  }
}

const isSettings =
  window.__FPASTE_WINDOW__ === "settings" ||
  getCurrentWindow().label === "settings";

window.addEventListener("error", (e) => {
  document.body.innerHTML = `<pre style="color:red;background:white;padding:16px;white-space:pre-wrap;font-size:14px">DIAG ERROR: ${e.message}\n${e.error?.stack ?? ""}</pre>`;
});
window.addEventListener("unhandledrejection", (e) => {
  document.body.innerHTML = `<pre style="color:red;background:white;padding:16px;white-space:pre-wrap;font-size:14px">DIAG REJECTION: ${String(e.reason)}\n${e.reason?.stack ?? ""}</pre>`;
});

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {error: Error | null}> {
  state = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }
  render() {
    if (this.state.error) {
      return <pre style={{color:'red', background:'white', padding:'16px', whiteSpace:'pre-wrap', fontSize:'14px'}}>
        ErrorBoundary: {this.state.error.message}{'\n'}{this.state.error.stack}
      </pre>;
    }
    return this.props.children;
  }
}

try {
  ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
    <React.StrictMode>
      <ErrorBoundary>
        {isSettings ? <Settings /> : <App />}
      </ErrorBoundary>
    </React.StrictMode>,
  );
} catch (err) {
  document.body.innerHTML = `<pre style="color:red;background:white;padding:16px;white-space:pre-wrap;font-size:14px">DIAG THROW: ${String(err)}\n${(err as Error)?.stack ?? ""}</pre>`;
}
