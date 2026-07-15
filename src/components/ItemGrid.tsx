import { useEffect, useRef } from "react";
import { useHistory } from "../stores/history";
import { useUi } from "../stores/ui";
import { dragRegionProps } from "../lib/dragRegion";
import { selectItem } from "../lib/api";
import { ItemCard } from "./ItemCard";

export function ItemGrid() {
  const items = useHistory((s) => s.items);
  const isLoading = useHistory((s) => s.isLoading);
  const hasMore = useHistory((s) => s.hasMore);
  const loadMore = useHistory((s) => s.loadMore);
  const remove = useHistory((s) => s.remove);
  const togglePinned = useHistory((s) => s.togglePinned);
  const selectedIndex = useHistory((s) => s.selectedIndex);
  const setSelectedIndex = useHistory((s) => s.setSelectedIndex);
  const isModo2 = useUi((s) => s.viewMode === "modo2");
  const sentinelRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<number, HTMLElement>>(new Map());

  // Sentinela observada a ~20% do fim ≈ gatilho aos 80% do conteúdo (spec §4).
  useEffect(() => {
    const sentinel = sentinelRef.current;
    const root = scrollRef.current;
    if (!sentinel || !root) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) void loadMore();
      },
      { root, rootMargin: "0px 0px 20% 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [loadMore]);

  // Acompanha a navegação por ↑/↓ rolando o item destacado para a área visível.
  useEffect(() => {
    const el = itemRefs.current.get(selectedIndex);
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex]);

  return (
    <div
      ref={scrollRef}
      className="fpaste-scroll grow overflow-y-auto px-5 pb-2 space-y-1.5"
      {...dragRegionProps(isModo2)}
    >
      {items.length === 0 && !isLoading && (
        <div
          className="h-full flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-500 text-sm gap-1 py-10"
          {...dragRegionProps(isModo2)}
        >
          <span className="text-2xl">📋</span>
          <span>Nada por aqui ainda</span>
          <span className="text-xs">Copie algo para começar</span>
        </div>
      )}

      {items.map((item, i) => (
        <div
          key={item.id}
          ref={(el) => {
            if (el) itemRefs.current.set(i, el);
            else itemRefs.current.delete(i);
          }}
        >
          <ItemCard
            item={item}
            selected={i === selectedIndex}
            onSelect={(id) => void selectItem(id)}
            onHover={() => setSelectedIndex(i)}
            onDelete={(id) => void remove(id)}
            onTogglePin={(id) => void togglePinned(id)}
          />
        </div>
      ))}

      <div ref={sentinelRef} className="h-px" />

      {isLoading && (
        <div className="flex justify-center py-2">
          <div
            className="w-4 h-4 rounded-full border-2 border-transparent animate-spin"
            style={{ borderTopColor: "var(--accent-color)", borderRightColor: "var(--accent-color)" }}
          />
        </div>
      )}
      {!hasMore && items.length > 0 && (
        <p className="text-center text-[11px] text-zinc-400 dark:text-zinc-500 py-1">
          fim do histórico
        </p>
      )}
    </div>
  );
}
