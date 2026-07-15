/**
 * No Modo 2 a janela fica fixa na tela, então liberamos arraste a partir de
 * qualquer área vazia (fora de cartões, botões e campos). O atributo só
 * dispara o drag quando o clique atinge o próprio elemento marcado — filhos
 * interativos continuam funcionando normalmente.
 */
export function dragRegionProps(active: boolean): Record<string, boolean> {
  return active ? { "data-tauri-drag-region": true } : {};
}
