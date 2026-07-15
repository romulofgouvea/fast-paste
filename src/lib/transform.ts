/** Transformações rápidas de texto oferecidas no menu de contexto do item. */

export function invertCase(text: string): string {
  return [...text]
    .map((ch) => (ch === ch.toUpperCase() ? ch.toLowerCase() : ch.toUpperCase()))
    .join("");
}

export function removeLineBreaks(text: string): string {
  return text.replace(/\s*[\r\n]+\s*/g, " ").trim();
}

const CONTROL_CHARS = new RegExp(
  "[" +
    String.fromCharCode(0) +
    "-" +
    String.fromCharCode(8) +
    String.fromCharCode(11) +
    String.fromCharCode(12) +
    String.fromCharCode(14) +
    "-" +
    String.fromCharCode(31) +
    String.fromCharCode(127) +
    "]",
  "g",
);

/** Remove caracteres de controle residuais — o conteúdo já é salvo como texto puro. */
export function asPlainText(text: string): string {
  return text.replace(CONTROL_CHARS, "").trim();
}
