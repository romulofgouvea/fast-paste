import { useEffect, useRef } from "react";
import { listen } from "@tauri-apps/api/event";
import { useHistory } from "./stores/history";
import { useUi } from "./stores/ui";
import { useTheme } from "./hooks/useTheme";
import { hideWindow, openSettings, selectItem } from "./lib/api";
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
      // Teclas 1–9 colam o n-ésimo item quando a busca está vazia (spec §7).
      if (/^[1-9]$/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const searchEmpty = !searchRef.current?.value;
        if (searchEmpty) {
          const item = useHistory.getState().items[Number(e.key) - 1];
          if (item) {
            e.preventDefault();
            void selectItem(item.id);
          }
        }
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

    // Expõe um helper global para suprimir o blur ao abrir settings
    (window as unknown as Record<string, unknown>).__fpasteOpenSettings = async () => {
      suppressBlur.current = true;
      // Dá um respiro para o event loop do frontend/WebView2 não congelar a
      // criação da nova janela que será despachada via IPC.
      setTimeout(() => {
        void openSettings();
      }, 50);
      // Restaura o blur após o foco mudar para a janela de settings
      setTimeout(() => { suppressBlur.current = false; }, 800);
    };
    window.addEventListener("blur", onBlur);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("blur", onBlur);
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
