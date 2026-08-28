import { useEffect, useRef } from "react";
import { listen } from "@tauri-apps/api/event";
import { useHistory } from "./stores/history";
import { useUi } from "./stores/ui";
import { useTheme } from "./hooks/useTheme";
import { hideWindow, selectItem } from "./lib/api";
import { registerBlurSuppressor } from "./lib/settingsWindow";
import { Header } from "./components/Header";
import { GroupBar } from "./components/GroupBar";
import { SearchBar } from "./components/SearchBar";
import { ItemGrid } from "./components/ItemGrid";
import { Footer } from "./components/Footer";

export default function App() {
  useTheme();
  const searchRef = useRef<HTMLInputElement>(null);
  const openedAt = useRef(0);
  const suppressBlur = useRef(false);

  useEffect(() => {
    const { refresh, setQuery } = useHistory.getState();
    void refresh();
    void useUi.getState().hydrate();

    // Novo item capturado pelo watcher Rust → recarrega a primeira página.
    const unNewItem = listen("clipboard://new-item", () => {
      void useHistory.getState().refresh();
    });

    // Janela aberta pela hotkey → busca limpa e focada, lista no topo.
    const unOpened = listen("fpaste://opened", () => {
      openedAt.current = Date.now();
      setQuery("");
      searchRef.current?.focus();
      searchRef.current?.select();
    });

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        void hideWindow();
        return;
      }
      // ↑/↓ navegam a lista independentemente do foco estar na busca;
      // Enter cola o item destacado (spec: "usar a seta para descer e selecionar").
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        useHistory.getState().moveSelection(e.key === "ArrowDown" ? 1 : -1);
        return;
      }
      if (e.key === "Enter") {
        const { items, selectedIndex } = useHistory.getState();
        const item = items[selectedIndex];
        if (item) {
          e.preventDefault();
          void selectItem(item.id);
        }
        return;
      }
    };
    window.addEventListener("keydown", onKeyDown);

    // Modo 1 (padrão): clicar fora fecha o FPaste, como um popup normal.
    // Modo 2: a janela fica aberta até a hotkey ser pressionada de novo ou
    // o botão de fechar ser clicado — ignora o blur completamente.
    const onBlur = () => {
      if (useUi.getState().viewMode === "modo2") return;
      if (suppressBlur.current) return;
      if (Date.now() - openedAt.current > 400) void hideWindow();
    };

    // Registra como suprimir o blur enquanto a janela de settings abre — evita
    // que a janela principal se feche ao perder o foco nesse intervalo.
    const unregisterSuppressor = registerBlurSuppressor((ms) => {
      suppressBlur.current = true;
      setTimeout(() => { suppressBlur.current = false; }, ms);
    });
    window.addEventListener("blur", onBlur);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("blur", onBlur);
      unregisterSuppressor();
      void unNewItem.then((fn) => fn());
      void unOpened.then((fn) => fn());
    };
  }, []);

  return (
    <div className="fpaste-shell fpaste-in h-full flex flex-col rounded-2xl overflow-hidden">
      <Header />
      <SearchBar ref={searchRef} />
      <GroupBar />
      <ItemGrid />
      <Footer />
    </div>
  );
}
