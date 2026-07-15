import { createPortal } from "react-dom";
import type { ClipItem } from "../../lib/api";

interface TooltipProps {
  anchorRect: DOMRect;
  item: ClipItem;
  fullText: string;
  highlighted: string | null;
  thumbSrc: string | null;
  scrollRef?: React.Ref<HTMLElement>;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

export function PreviewTooltip({ anchorRect, item, fullText, highlighted, thumbSrc, scrollRef, onMouseEnter, onMouseLeave }: TooltipProps) {
  const W = 300;
  const MAX_H = 380;
  const GAP = 12;

  // Centraliza o tooltip horizontalmente em relação ao item
  let left = anchorRect.left + anchorRect.width / 2 - W / 2;
  left = Math.max(GAP, Math.min(left, window.innerWidth - W - GAP));

  // Decide a posição vertical: mostra abaixo do cartão se houver espaço, senão acima.
  const GAP_Y = 6;
  const spaceBelow = window.innerHeight - anchorRect.bottom - GAP_Y;
  const spaceAbove = anchorRect.top - GAP_Y;

  let top: number | undefined;
  let bottom: number | undefined;
  let finalMaxH = MAX_H;

  if (spaceBelow >= 200 || spaceBelow >= spaceAbove) {
    top = anchorRect.bottom + GAP_Y;
    finalMaxH = Math.min(MAX_H, spaceBelow - GAP_Y);
  } else {
    bottom = window.innerHeight - anchorRect.top + GAP_Y;
    finalMaxH = Math.min(MAX_H, spaceAbove - GAP_Y);
  }

  return createPortal(
    <div
      onClick={(e) => e.stopPropagation()}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{ position: "fixed", left, top, bottom, width: W, maxHeight: finalMaxH, zIndex: 9999 }}
      className="rounded-xl shadow-2xl overflow-hidden border border-black/10 dark:border-white/10
                 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl animate-[fpaste-in_100ms_ease-out] cursor-default flex flex-col"
    >
      {item.type === "image" ? (
        <div className="flex items-center justify-center p-3 bg-black/5">
          {thumbSrc
            ? <img src={thumbSrc} alt="" className="max-w-full max-h-[340px] object-contain rounded-lg" />
            : <span className="text-4xl opacity-40">🖼️</span>
          }
        </div>
      ) : item.type === "code" ? (
        <pre ref={scrollRef as any} className="text-xs p-3 overflow-auto fpaste-scroll bg-zinc-950 text-zinc-100 leading-snug shrink" style={{ maxHeight: finalMaxH }}>
          {highlighted
            ? <code dangerouslySetInnerHTML={{ __html: highlighted }} />
            : <code>{fullText}</code>
          }
        </pre>
      ) : (
        <p ref={scrollRef as any} className="text-sm p-4 text-zinc-800 dark:text-zinc-100 whitespace-pre-wrap break-words overflow-auto fpaste-scroll leading-relaxed shrink" style={{ maxHeight: finalMaxH }}>
          {fullText}
        </p>
      )}
    </div>,
    document.body,
  );
}
