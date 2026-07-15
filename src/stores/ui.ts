import { create } from "zustand";
import { load } from "@tauri-apps/plugin-store";

export type ViewMode = "modo1" | "modo2";

const STORE_FILE = "settings.json";
const KEY = "viewMode";

interface UiState {
  viewMode: ViewMode;
  hydrated: boolean;
  toggleViewMode: () => void;
  /** Carrega o modo persistido; a janela principal monta uma vez, no startup. */
  hydrate: () => Promise<void>;
}

/**
 * Modo 1 (padrão) = clicar fora fecha o FPaste, como um popup normal.
 * Modo 2 = a janela permanece aberta até o usuário apertar a hotkey de
 * novo ou clicar em fechar — útil para colar vários itens em sequência.
 *
 * Persistido no mesmo `settings.json` do tema/accent/hotkey (via plugin-store),
 * unificando a estratégia de persistência — antes o viewMode usava localStorage.
 */
export const useUi = create<UiState>((set, get) => ({
  viewMode: "modo1",
  hydrated: false,

  toggleViewMode: () => {
    const next: ViewMode = get().viewMode === "modo1" ? "modo2" : "modo1";
    set({ viewMode: next });
    void load(STORE_FILE).then(async (store) => {
      await store.set(KEY, next);
      await store.save();
    });
  },

  hydrate: async () => {
    if (get().hydrated) return;
    const store = await load(STORE_FILE);
    const saved = await store.get<string>(KEY);
    set({ viewMode: saved === "modo2" ? "modo2" : "modo1", hydrated: true });
  },
}));
