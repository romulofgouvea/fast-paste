import { create } from "zustand";

export type ViewMode = "modo1" | "modo2";

const STORAGE_KEY = "fpaste-view-mode";

function loadViewMode(): ViewMode {
  return localStorage.getItem(STORAGE_KEY) === "modo2" ? "modo2" : "modo1";
}

interface UiState {
  viewMode: ViewMode;
  toggleViewMode: () => void;
}

/**
 * Modo 1 (padrão) = clicar fora fecha o FPaste, como um popup normal.
 * Modo 2 = a janela permanece aberta até o usuário apertar a hotkey de
 * novo ou clicar em fechar — útil para colar vários itens em sequência.
 * Persistido em localStorage — só afeta a janela principal.
 */
export const useUi = create<UiState>((set, get) => ({
  viewMode: loadViewMode(),
  toggleViewMode: () => {
    const next: ViewMode = get().viewMode === "modo1" ? "modo2" : "modo1";
    localStorage.setItem(STORAGE_KEY, next);
    set({ viewMode: next });
  },
}));
