import type { ReactNode } from "react";

/** Pílula selecionável (filtros de grupo). Ativa = fundo com a cor de destaque. */
export function Chip({ active, onClick, children }: {
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
