import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";

export interface MenuAction {
  label: string;
  onClick: () => void;
  danger?: boolean;
  divider?: boolean;
}

interface Props {
  x: number;
  y: number;
  actions: MenuAction[];
  onClose: () => void;
}

/** Menu de contexto simples, posicionado no cursor e clampado à janela. */
export function ContextMenu({ x, y, actions, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ x, y, ready: false });

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const { innerWidth, innerHeight } = window;
    const rect = el.getBoundingClientRect();
    setPos({
      x: Math.min(x, innerWidth - rect.width - 8),
      y: Math.min(y, innerHeight - rect.height - 8),
      ready: true,
    });
  }, [x, y]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("mousedown", onDown, true);
    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("mousedown", onDown, true);
      window.removeEventListener("keydown", onKey, true);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      style={{ left: pos.x, top: pos.y, visibility: pos.ready ? "visible" : "hidden" }}
      className="fixed z-50 min-w-44 py-1 rounded-lg border border-black/10 dark:border-white/15 bg-white/95 dark:bg-zinc-800/95 backdrop-blur-md shadow-lg text-sm"
    >
      {actions.map((a, i) => (
        <MenuItem key={i} action={a} onClose={onClose} />
      ))}
    </div>
  );
}

function MenuItem({ action, onClose }: { action: MenuAction; onClose: () => void }) {
  const content: ReactNode = (
    <button
      onClick={() => {
        action.onClick();
        onClose();
      }}
      className={`w-full text-left px-3 py-1.5 transition-colors ${
        action.danger
          ? "text-red-500 hover:bg-red-50 dark:hover:bg-red-950"
          : "text-zinc-700 dark:text-zinc-200 hover:bg-black/5 dark:hover:bg-white/10"
      }`}
    >
      {action.label}
    </button>
  );
  return action.divider ? (
    <>
      <div className="my-1 border-t border-black/10 dark:border-white/10" />
      {content}
    </>
  ) : (
    content
  );
}
