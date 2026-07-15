import { useEffect, useState, type ReactNode } from "react";
import { useHistory } from "../stores/history";
import { useUi } from "../stores/ui";
import { dragRegionProps } from "../lib/dragRegion";
import { listGroups, type Group } from "../lib/api";

export function GroupBar() {
  const [groups, setGroups] = useState<Group[]>([]);
  const groupFilter = useHistory((s) => s.groupFilter);
  const setGroupFilter = useHistory((s) => s.setGroupFilter);
  const isModo2 = useUi((s) => s.viewMode === "modo2");

  useEffect(() => { void listGroups().then(setGroups); }, []);

  // Sem grupos → não renderiza nada
  if (groups.length === 0) return null;

  return (
    <div
      className="flex items-center gap-1.5 px-3 pb-2 overflow-x-auto fpaste-scroll"
      {...dragRegionProps(isModo2)}
    >
      <Chip active={groupFilter === null} onClick={() => setGroupFilter(null)}>
        Tudo
      </Chip>
      {groups.map((g) => (
        <Chip key={g.id} active={groupFilter === g.id} onClick={() => setGroupFilter(g.id)}>
          {g.name}
        </Chip>
      ))}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`shrink-0 text-[11px] px-2.5 py-1 rounded-full transition-colors whitespace-nowrap ${
        active
          ? "text-white"
          : "bg-black/5 dark:bg-white/10 text-zinc-600 dark:text-zinc-300 hover:bg-black/10 dark:hover:bg-white/15"
      }`}
      style={active ? { backgroundColor: "var(--accent-color)" } : undefined}
    >
      {children}
    </button>
  );
}
