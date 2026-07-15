import { invoke } from "@tauri-apps/api/core";

export type ClipType = "text" | "link" | "code" | "image" | "files";

export interface ClipItem {
  id: number;
  type: ClipType;
  preview: string | null;
  content: string | null;
  pinned: boolean;
  timestamp: number;
  hasMedia: boolean;
  groupId: number | null;
}

export interface HistoryPage {
  items: ClipItem[];
  hasMore: boolean;
}

export interface Group {
  id: number;
  name: string;
}

export const PAGE_SIZE = 20;

export function getHistory(
  page: number,
  query?: string,
  typeFilter?: string,
  groupId?: number,
): Promise<HistoryPage> {
  return invoke<HistoryPage>("get_history", {
    page,
    pageSize: PAGE_SIZE,
    query: query || null,
    typeFilter: typeFilter || null,
    groupId: groupId ?? null,
  });
}

export function selectItem(id: number): Promise<void> {
  return invoke("select_item", { id });
}

export function pasteText(text: string): Promise<void> {
  return invoke("paste_text", { text });
}

export function deleteItem(id: number): Promise<void> {
  return invoke("delete_item", { id });
}

export function hideWindow(): Promise<void> {
  return invoke("hide_window");
}

export function setHotkey(shortcut: string): Promise<void> {
  return invoke("set_hotkey", { shortcut });
}

export function getHotkey(): Promise<string> {
  return invoke<string>("get_hotkey");
}

export function suspendHotkey(): Promise<void> {
  return invoke("suspend_hotkey");
}

export function resumeHotkey(): Promise<void> {
  return invoke("resume_hotkey");
}

export function getThumbnail(id: number): Promise<string> {
  return invoke<string>("get_thumbnail", { id });
}

export function togglePin(id: number): Promise<boolean> {
  return invoke<boolean>("toggle_pin", { id });
}

export function listGroups(): Promise<Group[]> {
  return invoke<Group[]>("list_groups");
}

export function createGroup(name: string): Promise<number> {
  return invoke<number>("create_group", { name });
}

export function deleteGroup(id: number): Promise<void> {
  return invoke("delete_group", { id });
}

export function setItemGroup(id: number, groupId: number | null): Promise<void> {
  return invoke("set_item_group", { id, groupId });
}

export function setAutoPaste(enabled: boolean): Promise<void> {
  return invoke("set_auto_paste", { enabled });
}

export function getAutoPaste(): Promise<boolean> {
  return invoke<boolean>("get_auto_paste");
}

export interface ImportSummary {
  imported: number;
  skipped: number;
}

export function exportBackup(password?: string): Promise<string> {
  return invoke<string>("export_backup", { password: password || null });
}

export function importBackup(password?: string): Promise<ImportSummary> {
  return invoke<ImportSummary>("import_backup", { password: password || null });
}

/**
 * Abre (ou traz ao foco) a janela de configurações. Delega ao comando Rust
 * `open_settings`, que apenas mostra a janela `settings` — declarada
 * estaticamente em tauri.conf.json e escondida na inicialização. Não há mais
 * criação dinâmica de WebviewWindow (causa da tela branca em runtime).
 */
export function openSettings(): Promise<void> {
  return invoke("open_settings");
}
