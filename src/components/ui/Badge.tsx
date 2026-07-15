import type { ReactNode } from "react";

/** Rótulo em pílula com a cor de destaque (ex.: badge de tipo do item). */
export function Badge({ children }: { children: ReactNode }) {
  return (
    <span
      className="shrink-0 px-1.5 py-px rounded-full text-white text-[9px] font-semibold uppercase tracking-wide"
      style={{ backgroundColor: "var(--accent-color)" }}
    >
      {children}
    </span>
  );
}
