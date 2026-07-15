import { useUi } from "../stores/ui";
import { hideWindow } from "../lib/api";

export function Header() {
  const viewMode = useUi((s) => s.viewMode);
  const toggleViewMode = useUi((s) => s.toggleViewMode);
  const isModo2 = viewMode === "modo2";

  return (
    <div
      data-tauri-drag-region
      className="flex items-center justify-between px-3 pt-2.5 pb-1 select-none"
    >
      <span className="text-xs font-semibold tracking-wide text-zinc-500 dark:text-zinc-400">
        FPaste
      </span>
      <div className="flex items-center gap-1.5">
        {/* Modo 1 / Modo 2 */}
        <button
          onClick={toggleViewMode}
          title="Alternar modo da janela"
          className={`px-2 py-0.5 rounded-md text-[11px] font-medium border transition-colors ${
            isModo2
              ? "border-[var(--accent-color)] text-[var(--accent-color)] bg-transparent"
              : "border-transparent text-white"
          }`}
          style={!isModo2 ? { backgroundColor: "var(--accent-color)" } : undefined}
        >
          {isModo2 ? "Modo 2" : "Modo 1"}
        </button>

        {/* Fechar */}
        <button
          onClick={() => void hideWindow()}
          title="Fechar"
          className="w-5 h-5 flex items-center justify-center rounded-md text-zinc-400 hover:bg-red-500 hover:!text-white transition-colors text-xs leading-none font-bold"
        >
          ✕
        </button>
      </div>
    </div>
  );
}
