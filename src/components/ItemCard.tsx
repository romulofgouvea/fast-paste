import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import hljs from "highlight.js/lib/common";
import {
  getThumbnail,
  listGroups,
  pasteText,
  setItemGroup,
  type ClipItem,
  type Group,
} from "../lib/api";
import { asPlainText, invertCase, removeLineBreaks } from "../lib/transform";
import { ContextMenu, type MenuAction } from "./ContextMenu";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<string, string> = {
  text: "Texto",
  link: "URL",
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
  return `${Math.floor(hours / 24)} d`;
}

function domainOf(url: string): string {
  try {
    return new URL(url.startsWith("www.") ? `https://${url}` : url).hostname.replace("www.", "");
  } catch {
    return url.slice(0, 32);
  }
}

function faviconOf(url: string): string {
  try {
    const domain = new URL(url.startsWith("www.") ? `https://${url}` : url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

/** Derivar um "título" curto do conteúdo */
function titleOf(item: ClipItem, fullText: string): string {
  if (item.type === "link") return domainOf(fullText);
  if (item.type === "image") return "Imagem";
  if (item.type === "files") return "Arquivo";
  // text / code — primeira linha não vazia
  const first = fullText.split("\n").find((l) => l.trim().length > 0) ?? fullText;
  return first.length > 48 ? first.slice(0, 48) + "…" : first;
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
  const W = 300;
  const MAX_H = 380;
  const GAP = 12;

  // A janela Tauri corta o que está fora dela.
  // Portanto, renderizamos o tooltip flutuando *dentro* da janela, encostado na direita.
  const left = window.innerWidth - W - GAP;
  
  // Centraliza verticalmente em relação ao item, mantendo dentro da tela
  let top = anchorRect.top + anchorRect.height / 2 - MAX_H / 2;
  top = Math.max(8, Math.min(top, window.innerHeight - MAX_H - 8));

  return createPortal(
    <div
      onClick={(e) => e.stopPropagation()}
      style={{ position: "fixed", left, top, width: W, maxHeight: MAX_H, zIndex: 9999 }}
      className="rounded-xl shadow-2xl overflow-hidden border border-black/10 dark:border-white/10
                 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl animate-[fpaste-in_100ms_ease-out] cursor-default"
    >
      {item.type === "image" ? (
        <div className="flex items-center justify-center p-3 bg-black/5">
          {thumbSrc
            ? <img src={thumbSrc} alt="" className="max-w-full max-h-[340px] object-contain rounded-lg" />
            : <span className="text-4xl opacity-40">🖼️</span>
          }
        </div>
      ) : item.type === "code" ? (
        <pre className="text-xs p-3 overflow-auto fpaste-scroll bg-zinc-950 text-zinc-100 leading-snug" style={{ maxHeight: MAX_H }}>
          {highlighted
            ? <code dangerouslySetInnerHTML={{ __html: highlighted }} />
            : <code>{fullText}</code>
          }
        </pre>
      ) : (
        <p className="text-sm p-4 text-zinc-800 dark:text-zinc-100 whitespace-pre-wrap break-words overflow-auto fpaste-scroll leading-relaxed" style={{ maxHeight: MAX_H }}>
          {fullText}
        </p>
      )}
    </div>,
    document.body,
  );
}

// ─── Thumbnail lazy ───────────────────────────────────────────────────────────

function LazyThumb({ id, onLoad }: { id: number; onLoad?: (src: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        obs.disconnect();
        getThumbnail(id).then((s) => { setSrc(s); onLoad?.(s); }).catch(() => setFailed(true));
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return (
    <div ref={ref} className="w-full h-full flex items-center justify-center">
      {src
        ? <img src={src} alt="" className="max-h-full max-w-full object-cover" />
        : <span className="text-xl opacity-30">{failed ? "⚠️" : "🖼️"}</span>
      }
    </div>
  );
}

// ─── Painel esquerdo ──────────────────────────────────────────────────────────

function LeftPanel({ item, fullText, highlighted, onThumb }: {
  item: ClipItem;
  fullText: string;
  highlighted: string | null;
  onThumb: (src: string) => void;
}) {
  if (item.type === "image") {
    return (
      <div className="w-20 shrink-0 bg-black/5 dark:bg-white/5 flex items-center justify-center overflow-hidden">
        <LazyThumb id={item.id} onLoad={onThumb} />
      </div>
    );
  }
  if (item.type === "code") {
    return (
      <div className="w-20 shrink-0 bg-zinc-900 overflow-hidden flex items-start p-1.5">
        <pre className="text-[8px] leading-[1.3] text-zinc-300 overflow-hidden select-none w-full">
          {highlighted
            ? <code dangerouslySetInnerHTML={{ __html: highlighted }} />
            : <code>{fullText.slice(0, 200)}</code>
          }
        </pre>
      </div>
    );
  }
  if (item.type === "link") {
    const favicon = faviconOf(fullText);
    return (
      <div className="w-20 shrink-0 bg-blue-50 dark:bg-blue-950/30 flex items-center justify-center overflow-hidden">
        {favicon
          ? <img src={favicon} alt="" className="w-8 h-8 rounded-md" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          : <span className="text-2xl opacity-40">🔗</span>
        }
      </div>
    );
  }
  // text / files — primeiras linhas do conteúdo
  return (
    <div className="w-20 shrink-0 bg-zinc-100 dark:bg-white/5 overflow-hidden flex items-start p-1.5">
      <p className="text-[8px] leading-[1.4] text-zinc-500 dark:text-zinc-400 break-words select-none w-full">
        {fullText.slice(0, 150)}
      </p>
    </div>
  );
}

// ─── ItemCard ─────────────────────────────────────────────────────────────────

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
            {item.type === "link" && faviconOf(fullText) && (
              <img
                src={faviconOf(fullText)}
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
