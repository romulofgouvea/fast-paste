import { describe, it, expect, beforeEach, vi } from "vitest";
import { useHistory } from "./history";
import type { ClipItem } from "../lib/api";

// Evita chamadas reais de IPC ao importar o store.
vi.mock("../lib/api", () => ({
  getHistory: vi.fn(),
  deleteItem: vi.fn(),
  togglePin: vi.fn(),
}));

function items(...ids: number[]): ClipItem[] {
  return ids.map((id) => ({
    id,
    type: "text",
    preview: null,
    content: `item ${id}`,
    pinned: false,
    timestamp: id,
    hasMedia: false,
    groupId: null,
  }));
}

describe("history store — moveSelection", () => {
  beforeEach(() => {
    useHistory.setState({ items: items(1, 2, 3), selectedIndex: 0 });
  });

  it("faz clamp nos limites da lista", () => {
    useHistory.getState().moveSelection(-1);
    expect(useHistory.getState().selectedIndex).toBe(0);

    useHistory.getState().moveSelection(1);
    expect(useHistory.getState().selectedIndex).toBe(1);

    useHistory.getState().moveSelection(10);
    expect(useHistory.getState().selectedIndex).toBe(2);
  });

  it("é no-op quando a lista está vazia", () => {
    useHistory.setState({ items: [], selectedIndex: 0 });
    useHistory.getState().moveSelection(1);
    expect(useHistory.getState().selectedIndex).toBe(0);
  });
});
