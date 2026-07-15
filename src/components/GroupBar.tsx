import { useEffect, useState, type ReactNode } from "react";
import { useHistory } from "../stores/history";
import { useUi } from "../stores/ui";
import { dragRegionProps } from "../lib/dragRegion";
import { createGroup, listGroups, type Group } from "../lib/api";

export function GroupBar() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const groupFilter = useHistory((s) => s.groupFilter);
  const setGroupFilter = useHistory((s) => s.setGroupFilter);
  const isModo2 = useUi((s) => s.viewMode === "modo2");

  const reload = () => void listGroups().then(setGroups);
  useEffect(reload, []);

  if (!adding && groups.length === 0) {
    return (
      <div className="px-3 pb-2" {...dragRegionProps(isModo2)}>
        <button
          onClick={() => setAdding(true)}
          className="text-[11px] px-2 py-1 rounded-full border border-dashed border-black/20 dark:border-white/20 text-zinc-500 dark:text-zinc-400 hover:border-[var(--accent-color)] hover:text-[var(--accent-color)] transition-colors"
        >
          + Criar grupo
        </button>
      </div>
    );
  }

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
      {adding ? (
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && name.trim()) {
              void createGroup(name.trim()).then(() => {
                setName("");
                setAdding(false);
                reload();
              });
            }
            if (e.key === "Escape") {
              setAdding(false);
              setName("");
            }
          }}
          onBlur={() => {
            setAdding(false);
            setName("");
          }}
          placeholder="Nome do grupo…"
          className="shrink-0 w-28 text-[11px] px-2 py-1 rounded-full bg-black/5 dark:bg-white/10 outline-none"
        />
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="shrink-0 text-[11px] px-2 py-1 rounded-full border border-dashed border-black/20 dark:border-white/20 text-zinc-500 dark:text-zinc-400 hover:border-[var(--accent-color)] hover:text-[var(--accent-color)] transition-colors"
        >
          + Grupo
        </button>
      )}
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
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
