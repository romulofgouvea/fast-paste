/** Conversões entre KeyboardEvent e strings de atalho do Tauri global-shortcut. */

const SPECIAL_CODES: Record<string, string> = {
  Space: "Space",
  Quote: "Quote",
  Backquote: "Backquote",
  Minus: "Minus",
  Equal: "Equal",
  BracketLeft: "BracketLeft",
  BracketRight: "BracketRight",
  Backslash: "Backslash",
  Semicolon: "Semicolon",
  Comma: "Comma",
  Period: "Period",
  Slash: "Slash",
  ArrowUp: "Up",
  ArrowDown: "Down",
  ArrowLeft: "Left",
  ArrowRight: "Right",
  Enter: "Enter",
  Tab: "Tab",
  Delete: "Delete",
  Home: "Home",
  End: "End",
  PageUp: "PageUp",
  PageDown: "PageDown",
};

export function isModifierKey(e: KeyboardEvent): boolean {
  return ["Control", "Shift", "Alt", "Meta"].includes(e.key);
}

export function currentModifiers(e: KeyboardEvent): string[] {
  const mods: string[] = [];
  if (e.ctrlKey || e.metaKey) mods.push("CommandOrControl");
  if (e.altKey) mods.push("Alt");
  if (e.shiftKey) mods.push("Shift");
  return mods;
}

/**
 * Consolida o atalho quando uma tecla final (não-modificadora) é pressionada.
 * Retorna null se a tecla não é suportada ou se não há modificador.
 */
export function eventToShortcut(e: KeyboardEvent): string | null {
  const mods = currentModifiers(e);
  if (mods.length === 0) return null;

  const code = e.code;
  let key: string | null = null;
  if (/^Key[A-Z]$/.test(code)) key = code.slice(3);
  else if (/^Digit[0-9]$/.test(code)) key = code.slice(5);
  else if (/^F([1-9]|1[0-9]|2[0-4])$/.test(code)) key = code;
  else if (code in SPECIAL_CODES) key = SPECIAL_CODES[code];

  if (!key) return null;
  return [...mods, key].join("+");
}

const DISPLAY_MAP: Record<string, string> = {
  CommandOrControl: navigator.userAgent.includes("Mac") ? "⌘" : "Ctrl",
  Control: "Ctrl",
  Alt: "Alt",
  Shift: "Shift",
  Super: "Win",
  Quote: "'",
  Backquote: "`",
  Space: "Espaço",
  Up: "↑",
  Down: "↓",
  Left: "←",
  Right: "→",
};

/** "CommandOrControl+Quote" → "Ctrl + '" para exibição na UI. */
export function displayShortcut(shortcut: string): string {
  return shortcut
    .split("+")
    .map((part) => DISPLAY_MAP[part] ?? part)
    .join(" + ");
}
