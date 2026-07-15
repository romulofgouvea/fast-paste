import { openSettings } from "./api";

/**
 * Abertura da janela de configurações a partir da janela principal.
 *
 * Antes isso era um helper pendurado em `window.__fpasteOpenSettings`, escrito
 * por App.tsx e lido por Footer.tsx (acoplamento por variável global e casts
 * `as unknown as Record<...>`). Agora é um módulo tipado: App registra um
 * "supressor de blur" — para a janela principal não se fechar ao perder o foco
 * enquanto a de settings abre — e qualquer componente chama openSettingsWindow().
 */
type BlurSuppressor = (durationMs: number) => void;

let blurSuppressor: BlurSuppressor | null = null;

/** App registra como suprimir seu próprio blur; devolve a função de baixa. */
export function registerBlurSuppressor(fn: BlurSuppressor): () => void {
  blurSuppressor = fn;
  return () => {
    if (blurSuppressor === fn) blurSuppressor = null;
  };
}

export async function openSettingsWindow(): Promise<void> {
  // Suprime o blur enquanto o foco migra para a nova janela.
  blurSuppressor?.(800);
  // Respiro para o event loop do WebView2 não congelar a criação da janela.
  await new Promise((resolve) => setTimeout(resolve, 50));
  await openSettings();
}
