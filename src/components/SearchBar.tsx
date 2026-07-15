import { forwardRef } from "react";
import { useHistory } from "../stores/history";
import { useUi } from "../stores/ui";
import { dragRegionProps } from "../lib/dragRegion";

export const SearchBar = forwardRef<HTMLInputElement>(function SearchBar(_, ref) {
  const rawQuery = useHistory((s) => s.rawQuery);
  const setQuery = useHistory((s) => s.setQuery);
  const isModo2 = useUi((s) => s.viewMode === "modo2");

  return (
    <div className="px-3 pt-2 pb-2" {...dragRegionProps(isModo2)}>
      <div
        className="flex items-center gap-2 rounded-xl px-3 py-2
                   bg-white/60 dark:bg-white/[0.08]
                   border border-black/[0.07] dark:border-white/[0.10]"
      >
        <svg
          className="w-4 h-4 shrink-0 text-zinc-400 dark:text-zinc-500"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" strokeLinecap="round" />
        </svg>
        <input
          ref={ref}
          type="text"
          value={rawQuery}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar… (tipo:link, tipo:código)"
          className="w-full bg-transparent outline-none text-sm text-zinc-800 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500"
          autoFocus
          spellCheck={false}
        />
        {rawQuery && (
          <button
            onClick={() => setQuery("")}
            className="shrink-0 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors text-xs leading-none"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
});
