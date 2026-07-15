import type { ClipItem } from "../../lib/api";
import { faviconOf } from "../../lib/clipItem";
import { LazyThumb } from "./LazyThumb";

/** Painel esquerdo do cartão — preview visual conforme o tipo do item. */
export function LeftPanel({ item, fullText, highlighted, onThumb }: {
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
