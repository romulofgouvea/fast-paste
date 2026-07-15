import type { ClipItem } from "./api";

/** Rótulos exibidos no badge de tipo do cartão. */
export const TYPE_LABEL: Record<string, string> = {
  text: "Texto",
  link: "URL",
  code: "Código",
  image: "Imagem",
  files: "Arquivo",
};

/** "há quanto tempo" compacto: agora / N min / N h / N d. */
export function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return "agora";
  if (min < 60) return `${min} min`;
  const hours = Math.floor(min / 60);
  if (hours < 24) return `${hours} h`;
  return `${Math.floor(hours / 24)} d`;
}

/** Domínio legível de uma URL (sem "www."), com fallback truncado. */
export function domainOf(url: string): string {
  try {
    return new URL(url.startsWith("www.") ? `https://${url}` : url).hostname.replace("www.", "");
  } catch {
    return url.slice(0, 32);
  }
}

/** URL do favicon (via serviço do Google), ou "" se a URL for inválida. */
export function faviconOf(url: string): string {
  try {
    const domain = new URL(url.startsWith("www.") ? `https://${url}` : url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

/** Deriva um "título" curto do conteúdo, conforme o tipo do item. */
export function titleOf(item: ClipItem, fullText: string): string {
  if (item.type === "link") return domainOf(fullText);
  if (item.type === "image") return "Imagem";
  if (item.type === "files") return "Arquivo";
  // text / code — primeira linha não vazia
  const first = fullText.split("\n").find((l) => l.trim().length > 0) ?? fullText;
  return first.length > 48 ? first.slice(0, 48) + "…" : first;
}
