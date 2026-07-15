import { useHistory } from "../stores/history";
import { useUi } from "../stores/ui";
import { dragRegionProps } from "../lib/dragRegion";
import { openSettingsWindow } from "../lib/settingsWindow";

export function Footer() {
  const groupFilter = useHistory((s) => s.groupFilter);
  const setGroupFilter = useHistory((s) => s.setGroupFilter);
  const isModo2 = useUi((s) => s.viewMode === "modo2");

  return (
    <div
      className="flex items-center justify-between px-3 py-1.5 border-t border-black/10 dark:border-white/10 text-[11px] text-zinc-500 dark:text-zinc-400"
      {...dragRegionProps(isModo2)}
    >
      <div>
        {groupFilter != null && (
          <button
            onClick={() => setGroupFilter(null)}
            className="underline hover:text-[var(--accent-color)]"
          >
            Limpar filtro de grupo
          </button>
        )}
      </div>

      {/* Botão Configurações — mesmo estilo texto do Modo 1/2 */}
      <button
        onClick={() => void openSettingsWindow()}
        title="Configurações"
        className="px-2 py-0.5 rounded-md text-[11px] font-medium border transition-colors
                   border-transparent text-zinc-500 dark:text-zinc-400
                   hover:border-black/15 dark:hover:border-white/20
                   hover:bg-black/5 dark:hover:bg-white/10
                   hover:text-zinc-800 dark:hover:text-zinc-200"
      >
        Config
      </button>
    </div>
  );
}
