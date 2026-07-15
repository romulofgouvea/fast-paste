import { forwardRef } from "react";
import { useHistory } from "../stores/history";
import { useUi } from "../stores/ui";
import { dragRegionProps } from "../lib/dragRegion";

export const SearchBar = forwardRef<HTMLInputElement>(function SearchBar(_, ref) {
  const rawQuery = useHistory((s) => s.rawQuery);
  const setQuery = useHistory((s) => s.setQuery);
  const isModo2 = useUi((s) => s.viewMode === "modo2");

  return (
    <div className="px-3 pt-3 pb-2" {...dragRegionProps(isModo2)}>
      <div className="flex items-center gap-2 rounded-xl bg-black/5 dark:bg-white/10 px-3 py-2 focus-within:ring-2 ring-[var(--accent-color)] transition-shadow">
        <svg
          className="w-4 h-4 shrink-0 text-zinc-500 dark:text-zinc-400"
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
      </div>
    </div>
  );
});
