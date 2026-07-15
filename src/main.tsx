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

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="h-full flex flex-col items-center justify-center gap-3 p-6 text-center text-zinc-600 dark:text-zinc-300">
          <span className="text-3xl">⚠️</span>
          <p className="text-sm font-medium">Algo deu errado ao carregar o FPaste.</p>
          <button
            onClick={() => window.location.reload()}
            className="px-3 py-1.5 rounded-lg text-sm text-white"
            style={{ backgroundColor: "var(--accent-color)" }}
          >
            Recarregar
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>{isSettings ? <Settings /> : <App />}</ErrorBoundary>
  </React.StrictMode>,
);
