import { createPortal } from "react-dom";
import type { ClipItem } from "../../lib/api";

interface TooltipProps {
  anchorRect: DOMRect;
  item: ClipItem;
  fullText: string;
  highlighted: string | null;
  thumbSrc: string | null;
}

/** Tooltip flutuante com o preview completo do item, ancorado ao cartão. */
export function PreviewTooltip({ anchorRect, item, fullText, highlighted, thumbSrc }: TooltipProps) {
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
