import { useEffect } from "react";
import { load } from "@tauri-apps/plugin-store";
import { listen } from "@tauri-apps/api/event";

export type ThemeMode = "light" | "dark" | "system";

export const ACCENT_PRESETS: Record<string, string> = {
  "Azul Clássico": "#3b82f6",
  "Roxo Moderno": "#8b5cf6",
  "Verde Esmeralda": "#10b981",
  "Laranja Cítrico": "#f97316",
};

async function readSettings(): Promise<{ theme: ThemeMode; accent: string }> {
  const store = await load("settings.json");
  const theme = ((await store.get<string>("theme")) as ThemeMode) || "system";
  const accent = (await store.get<string>("accent")) || ACCENT_PRESETS["Azul Clássico"];
  return { theme, accent };
}

function applyTheme(theme: ThemeMode, accent: string) {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = theme === "dark" || (theme === "system" && prefersDark);
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.style.setProperty("--accent-color", accent);
}

/**
 * Aplica tema (claro/escuro/sistema) e accent color na raiz do documento.
 * Reage a mudanças do SO (prefers-color-scheme) e a alterações feitas na
 * janela de configurações (evento fpaste://settings-changed).
 */
export function useTheme() {
  useEffect(() => {
    let mode: ThemeMode = "system";
    let accent = ACCENT_PRESETS["Azul Clássico"];

    const sync = () => applyTheme(mode, accent);
    const reload = () =>
      readSettings().then((s) => {
        mode = s.theme;
        accent = s.accent;
        sync();
      });

    void reload();

    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", sync);
    const unlisten = listen("fpaste://settings-changed", reload);

    return () => {
      media.removeEventListener("change", sync);
      void unlisten.then((fn) => fn());
    };
  }, []);
}
