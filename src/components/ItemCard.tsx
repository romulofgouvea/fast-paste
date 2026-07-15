import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import hljs from "highlight.js/lib/common";
import { getThumbnail, listGroups, pasteText, setItemGroup, type ClipItem, type Group } from "../lib/api";
import { asPlainText, invertCase, removeLineBreaks } from "../lib/transform";
import { ContextMenu, type MenuAction } from "./ContextMenu";

const TYPE_LABEL: Record<string, string> = {
  text: "Texto",
  link: "Link",
  code: "Código",
  image: "Imagem",
  files: "Arquivo",
};

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "agora";
  if (min < 60) return `${min} min`;
  const hours = Math.floor(min / 60);
  if (hours < 24) return `${hours} h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} d`;
  return new Date(ts).toLocaleDateString("pt-BR");
}

function faviconFor(url: string): string {
  try {
    const domain = new URL(url.startsWith("www.") ? `https://${url}` : url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

// ─── Tooltip de preview ───────────────────────────────────────────────────────

interface TooltipProps {
  anchorRect: DOMRect;
  item: ClipItem;
  fullText: string;
  highlighted: string | null;
  thumbSrc: string | null;
}

function PreviewTooltip({ anchorRect, item, fullText, highlighted, thumbSrc }: TooltipProps) {
  const TOOLTIP_W = 320;
  const TOOLTIP_MAX_H = 400;
  const GAP = 8;

  // Posiciona à direita do item; se não couber, vai à esquerda
  const spaceRight = window.innerWidth - anchorRect.right;
  const spaceLeft = anchorRect.left;
  let left: number;
  if (spaceRight >= TOOLTIP_W + GAP) {
    left = anchorRect.right + GAP;
  } else if (spaceLeft >= TOOLTIP_W + GAP) {
    left = anchorRect.left - TOOLTIP_W - GAP;
  } else {
    left = Math.max(8, anchorRect.left);
  }

  // Alinha verticalmente ao centro do item, sem sair da tela
  let top = anchorRect.top + anchorRect.height / 2 - TOOLTIP_MAX_H / 2;
  top = Math.max(8, Math.min(top, window.innerHeight - TOOLTIP_MAX_H - 8));

  return createPortal(
    <div
      style={{
        position: "fixed",
        left,
        top,
        width: TOOLTIP_W,
        maxHeight: TOOLTIP_MAX_H,
        zIndex: 9999,
        pointerEvents: "none",
      }}
      className="rounded-xl border border-black/10 dark:border-white/15 shadow-2xl overflow-hidden
                 bg-white/95 dark:bg-zinc-900/95 backdrop-filter backdrop-blur-xl
                 animate-[fpaste-in_100ms_ease-out]"
    >
      {item.type === "image" ? (
        <div className="flex items-center justify-center p-3 bg-black/5 dark:bg-white/5" style={{ maxHeight: TOOLTIP_MAX_H }}>
          {thumbSrc ? (
            <img src={thumbSrc} alt="" className="max-w-full max-h-full object-contain rounded-lg" />
          ) : (
            <span className="text-4xl opacity-40">🖼️</span>
          )}
        </div>
      ) : item.type === "code" ? (
        <pre className="text-xs p-3 overflow-auto fpaste-scroll bg-zinc-950 text-zinc-100 leading-snug" style={{ maxHeight: TOOLTIP_MAX_H }}>
          {highlighted ? (
            <code dangerouslySetInnerHTML={{ __html: highlighted }} />
          ) : (
            <code>{fullText}</code>
          )}
        </pre>
      ) : (
        <p className="text-sm p-4 text-zinc-800 dark:text-zinc-100 whitespace-pre-wrap break-words overflow-auto fpaste-scroll leading-relaxed" style={{ maxHeight: TOOLTIP_MAX_H }}>
          {fullText}
        </p>
      )}
    </div>,
    document.body,
  );
}

// ─── Thumbnail lazy para o card (tamanho fixo) ───────────────────────────────

function LazyThumbnail({ id, onLoad }: { id: number; onLoad?: (src: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        observer.disconnect();
        getThumbnail(id)
          .then((s) => { setSrc(s); onLoad?.(s); })
          .catch(() => setFailed(true));
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [id, onLoad]);

  return (
    <div className="h-16 rounded-lg overflow-hidden bg-black/5 dark:bg-white/5 flex items-center justify-center">
      <div ref={ref} className="w-full h-full flex items-center justify-center">
        {src ? (
          <img src={src} alt="" className="max-h-full max-w-full object-contain" />
        ) : (
          <span className="text-xl opacity-40">{failed ? "⚠️" : "🖼️"}</span>
        )}
      </div>
    </div>
  );
}

// ─── ItemCard ─────────────────────────────────────────────────────────────────

interface Props {
  item: ClipItem;
  index: number;
  selected?: boolean;
  onSelect: (id: number) => void;
  onHover?: () => void;
  onDelete: (id: number) => void;
  onTogglePin: (id: number) => void;
}

export const ItemCard = memo(function ItemCard({
  item,
  index,
  selected,
  onSelect,
  onHover,
  onDelete,
  onTogglePin,
}: Props) {
  const fullText = item.content ?? item.preview ?? "";

  const highlighted = useMemo(() => {
    if (item.type !== "code") return null;
    try {
      return hljs.highlightAuto(fullText).value;
    } catch {
      return null;
    }
  }, [item.type, fullText]);

  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [hovered, setHovered] = useState(false);
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);
  const [thumbSrc, setThumbSrc] = useState<string | null>(null);
  const cardRef = useRef<HTMLButtonElement>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    onHover?.();
    hoverTimer.current = setTimeout(() => {
      if (cardRef.current) {
        setAnchorRect(cardRef.current.getBoundingClientRect());
        setHovered(true);
      }
    }, 400);
  }, [onHover]);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setHovered(false);
  }, []);

  const openMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    void listGroups().then(setGroups);
    setMenu({ x: e.clientX, y: e.clientY });
  };

  const canTransform = item.type === "text" || item.type === "code" || item.type === "link";

  const actions: MenuAction[] = [
    {
      label: item.pinned ? "Desafixar" : "Fixar",
      onClick: () => onTogglePin(item.id),
    },
    ...(canTransform
      ? [
          { label: "Colar como texto puro", onClick: () => void pasteText(asPlainText(fullText)) },
          { label: "Inverter maiúsculas/minúsculas", onClick: () => void pasteText(invertCase(fullText)) },
          { label: "Remover quebras de linha", onClick: () => void pasteText(removeLineBreaks(fullText)) },
        ]
      : []),
    { label: "Sem grupo", onClick: () => void setItemGroup(item.id, null), divider: true },
    ...groups.map((g) => ({
      label: `Mover para "${g.name}"`,
      onClick: () => void setItemGroup(item.id, g.id),
    })),
    { label: "Excluir", onClick: () => onDelete(item.id), danger: true, divider: true },
  ];

  // Conteúdo interno do card — tamanho fixo, sem expandir
  const cardContent = () => {
    if (item.type === "link") {
      return (
        <div className="flex items-center gap-2 h-8">
          {faviconFor(fullText) && (
            <img src={faviconFor(fullText)} alt="" className="w-4 h-4 rounded-sm shrink-0" />
          )}
          <span className="text-sm truncate text-[var(--accent-color)] underline-offset-2 hover:underline">
            {fullText}
          </span>
        </div>
      );
    }
    if (item.type === "image") {
      return <LazyThumbnail id={item.id} onLoad={setThumbSrc} />;
    }
    if (item.type === "code") {
      return (
        <pre className="rounded-lg bg-zinc-900 text-zinc-100 text-xs p-2 h-12 overflow-hidden leading-snug">
          {highlighted ? (
            <code dangerouslySetInnerHTML={{ __html: highlighted }} />
          ) : (
            <code>{fullText}</code>
          )}
        </pre>
      );
    }
    // text / files
    return (
      <p className="text-sm text-zinc-800 dark:text-zinc-100 line-clamp-2 break-words leading-snug h-10 overflow-hidden">
        {fullText}
      </p>
    );
  };

  return (
    <>
      <button
        ref={cardRef}
        onClick={() => onSelect(item.id)}
        onContextMenu={openMenu}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className={`group w-full text-left rounded-xl px-3 py-2 border transition-colors cursor-pointer ${
          selected
            ? "bg-white/90 dark:bg-white/[0.12] border-[var(--accent-color)] ring-1 ring-[var(--accent-color)]"
            : "bg-white/55 dark:bg-white/[0.06] hover:bg-white/85 dark:hover:bg-white/[0.12] border-black/5 dark:border-white/10"
        }`}
      >
        {cardContent()}

        <div className="mt-1.5 flex items-center gap-2 text-[11px] text-zinc-500 dark:text-zinc-400">
          {index < 9 && (
            <kbd className="px-1 rounded bg-black/10 dark:bg-white/15 font-mono text-[10px]">
              {index + 1}
            </kbd>
          )}
          <span
            className="px-1.5 py-px rounded-full text-white text-[10px] font-medium shrink-0"
            style={{ backgroundColor: "var(--accent-color)" }}
          >
            {TYPE_LABEL[item.type] ?? item.type}
          </span>
          <span className="shrink-0">{relativeTime(item.timestamp)}</span>
          <span className="grow" />
          <span
            role="button"
            tabIndex={-1}
            onClick={(e) => {
              e.stopPropagation();
              onTogglePin(item.id);
            }}
            className={`transition-opacity px-1 ${
              item.pinned ? "opacity-100 text-[var(--accent-color)]" : "opacity-0 group-hover:opacity-100 hover:text-[var(--accent-color)]"
            }`}
            title={item.pinned ? "Desafixar" : "Fixar"}
          >
            📌
          </span>
          <span
            role="button"
            tabIndex={-1}
            onClick={(e) => {
              e.stopPropagation();
              onDelete(item.id);
            }}
            className="opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity px-1"
            title="Excluir"
          >
            ✕
          </span>
        </div>
      </button>

      {/* Tooltip de preview */}
      {hovered && anchorRect && (
        <PreviewTooltip
          anchorRect={anchorRect}
          item={item}
          fullText={fullText}
          highlighted={highlighted}
          thumbSrc={thumbSrc}
        />
      )}

      <ItemCardMenuPortal menu={menu} actions={actions} onClose={() => setMenu(null)} />
    </>
  );
});

/**
 * Wrapper que injeta o menu de contexto via portal — o ContextMenu contém
 * `<button>`s e não pode ser filho do `<button>` do cartão (HTML inválido).
 */
export function ItemCardMenuPortal({
  menu,
  actions,
  onClose,
}: {
  menu: { x: number; y: number } | null;
  actions: MenuAction[];
  onClose: () => void;
}) {
  if (!menu) return null;
  return createPortal(
    <ContextMenu x={menu.x} y={menu.y} actions={actions} onClose={onClose} />,
    document.body,
  );
}
