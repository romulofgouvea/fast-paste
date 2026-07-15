import { useEffect, useRef, useState } from "react";
import { getThumbnail } from "../../lib/api";

/**
 * Miniatura de imagem carregada sob demanda: só busca (e decifra no backend) a
 * thumbnail quando o elemento entra na área visível (IntersectionObserver).
 */
export function LazyThumb({ id, onLoad }: { id: number; onLoad?: (src: string) => void }) {
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
