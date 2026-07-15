import type { ClipType } from "./api";

const TYPE_ALIASES: Record<string, ClipType> = {
  texto: "text",
  text: "text",
  link: "link",
  url: "link",
  codigo: "code",
  código: "code",
  code: "code",
  imagem: "image",
  image: "image",
  img: "image",
  arquivo: "files",
  arquivos: "files",
  file: "files",
  files: "files",
};

export interface ParsedQuery {
  search: string;
  typeFilter?: ClipType;
}

/**
 * Extrai filtros estilo comando ("tipo:imagem", "type:link") da busca,
 * devolvendo o texto restante como termo livre.
 */
export function parseQuery(raw: string): ParsedQuery {
  const words: string[] = [];
  let typeFilter: ClipType | undefined;

  for (const token of raw.split(/\s+/)) {
    const match = token.match(/^(tipo|type):(.+)$/i);
    if (match) {
      const alias = TYPE_ALIASES[match[2].toLowerCase()];
      if (alias) {
        typeFilter = alias;
        continue;
      }
    }
    if (token) words.push(token);
  }

  return { search: words.join(" "), typeFilter };
}
