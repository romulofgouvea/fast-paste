import { memo, useCallback, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import hljs from "highlight.js/lib/common";
import {
  listGroups,
  pasteText,
  setItemGroup,
  type ClipItem,
  type Group,
} from "../lib/api";
import { asPlainText, invertCase, removeLineBreaks } from "../lib/transform";
import { TYPE_LABEL, faviconOf, relativeTime, titleOf } from "../lib/clipItem";
import { ContextMenu, type MenuAction } from "./ContextMenu";
import { PreviewTooltip } from "./itemCard/PreviewTooltip";
import { LeftPanel } from "./itemCard/LeftPanel";

interface Props {
  item: ClipItem;
  selected?: boolean;
  onSelect: (id: number) => void;
  onHover?: () => void;
  onDelete: (id: number) => void;
  onTogglePin: (id: number) => void;
}

export const ItemCard = memo(function ItemCard({ item, selected, onSelect, onHover, onDelete, onTogglePin }: Props) {
  const fullText = item.content ?? item.preview ?? "";
  const title = titleOf(item, fullText);
  const favicon = useMemo(() => (item.type === "link" ? faviconOf(fullText) : ""), [item.type, fullText]);

  const highlighted = useMemo(() => {
    if (item.type !== "code") return null;
    try { return hljs.highlightAuto(fullText).value; } catch { return null; }
  }, [item.type, fullText]);

  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [hovered, setHovered] = useState(false);
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);
  const [thumbSrc, setThumbSrc] = useState<string | null>(null);
  const cardRef = useRef<HTMLButtonElement>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = useCallback(() => {
    // Timer do tooltip — independente do onHover para não ser cancelado por re-renders
    hoverTimer.current = setTimeout(() => {
      if (cardRef.current) {
        setAnchorRect(cardRef.current.getBoundingClientRect());
        setHovered(true);
      }
    }, 400);
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    setHovered(false);
  }, []);

  const handleDragStart = useCallback((e: React.DragEvent) => {
    if (item.type === "text" || item.type === "code") {
      const fileName = `fpaste-${item.id}.txt`;
      // O Chromium/WebView2 entende o formato MIME:filename:URL para criar arquivos via drag
      const downloadUrl = `text/plain:${fileName}:data:text/plain;charset=utf-8,${encodeURIComponent(fullText)}`;
      e.dataTransfer.setData("DownloadURL", downloadUrl);
      e.dataTransfer.effectAllowed = "copy";
    }
  }, [item.type, item.id, fullText]);

  const openMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    void listGroups().then(setGroups);
    setMenu({ x: e.clientX, y: e.clientY });
  };

  const canTransform = item.type === "text" || item.type === "code" || item.type === "link";
  const actions: MenuAction[] = [
    { label: item.pinned ? "Desafixar" : "Fixar", onClick: () => onTogglePin(item.id) },
    ...(canTransform ? [
      { label: "Colar como texto puro", onClick: () => void pasteText(asPlainText(fullText)) },
      { label: "Inverter maiúsculas/minúsculas", onClick: () => void pasteText(invertCase(fullText)) },
      { label: "Remover quebras de linha", onClick: () => void pasteText(removeLineBreaks(fullText)) },
    ] : []),
    { label: "Sem grupo", onClick: () => void setItemGroup(item.id, null), divider: true },
    ...groups.map((g) => ({ label: `Mover para "${g.name}"`, onClick: () => void setItemGroup(item.id, g.id) })),
    { label: "Excluir", onClick: () => onDelete(item.id), danger: true, divider: true },
  ];

  // Linha de subtítulo abaixo do badge (ex: domínio para links)
  const subtitle = item.type === "link" ? fullText.slice(0, 60) : null;

  return (
    <>
      <button
        ref={cardRef}
        draggable={item.type === "text" || item.type === "code"}
        onDragStart={handleDragStart}
        onClick={() => onSelect(item.id)}
        onContextMenu={openMenu}
        onMouseEnter={() => { onHover?.(); handleMouseEnter(); }}
        onMouseLeave={handleMouseLeave}
        className={`group relative w-full text-left rounded-xl border transition-all cursor-pointer overflow-hidden flex items-stretch h-[72px] ${
          selected
            ? "bg-white dark:bg-white/[0.10] border-[var(--accent-color)] ring-1 ring-[var(--accent-color)] shadow-sm"
            : "bg-white/70 dark:bg-white/[0.05] hover:bg-white dark:hover:bg-white/[0.10] border-black/[0.06] dark:border-white/[0.08] hover:border-black/[0.12] dark:hover:border-white/[0.15] hover:shadow-sm"
        }`}
      >
        {/* Painel esquerdo — preview visual */}
        <LeftPanel item={item} fullText={fullText} highlighted={highlighted} onThumb={setThumbSrc} />

        {/* Painel direito — conteúdo textual */}
        <div className="flex-1 min-w-0 flex flex-col justify-between px-3 py-2 pr-2">
          {/* Linha 1: título + favicon */}
          <div className="flex items-start gap-1.5 pr-14">
            <span className="flex-1 min-w-0 text-[13px] font-semibold text-zinc-800 dark:text-zinc-100 truncate leading-tight">
              {title}
            </span>
            {favicon && (
              <img
                src={favicon}
                alt=""
                className="shrink-0 w-4 h-4 rounded-sm mt-px"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
              />
            )}
          </div>

          {/* Linha 2: badge tipo + subtítulo */}
          <div className="flex items-center gap-1.5 min-w-0">
            <span
              className="shrink-0 px-1.5 py-px rounded-full text-white text-[9px] font-semibold uppercase tracking-wide"
              style={{ backgroundColor: "var(--accent-color)" }}
            >
              {TYPE_LABEL[item.type] ?? item.type}
            </span>
            {subtitle && (
              <span className="text-[10px] text-zinc-500 dark:text-zinc-400 truncate">{subtitle}</span>
            )}
          </div>
        </div>

        {/* Hora — bottom-right fixo */}
        <span className="absolute bottom-1.5 right-2 text-[10px] text-zinc-400 dark:text-zinc-500 pointer-events-none">
          {relativeTime(item.timestamp)}
        </span>

        {/* Pin — sempre visível se fixado, senão aparece só no hover */}
        <span
          role="button"
          tabIndex={-1}
          onClick={(e) => { e.stopPropagation(); onTogglePin(item.id); }}
          title={item.pinned ? "Desafixar" : "Fixar"}
          className={`absolute top-1.5 right-7 w-5 h-5 flex items-center justify-center rounded text-[11px] transition-colors
            ${item.pinned
              ? "opacity-100 text-[var(--accent-color)]"
              : "opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-[var(--accent-color)] hover:bg-black/5 dark:hover:bg-white/10"
            }`}
        >
          📌
        </span>

        {/* Excluir — só no hover */}
        <div className="absolute top-1.5 right-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <span
            role="button"
            tabIndex={-1}
            onClick={(e) => { e.stopPropagation(); onDelete(item.id); }}
            title="Excluir"
            className="w-5 h-5 flex items-center justify-center rounded text-[11px] text-zinc-400
                       hover:text-white hover:bg-red-500 transition-colors"
          >
            ✕
          </span>
        </div>
      </button>

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

export function ItemCardMenuPortal({ menu, actions, onClose }: {
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
