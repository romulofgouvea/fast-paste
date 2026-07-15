import { create } from "zustand";
import { getHistory, deleteItem, togglePin, type ClipItem } from "../lib/api";
import { parseQuery } from "../lib/parseQuery";

interface HistoryState {
  items: ClipItem[];
  page: number;
  hasMore: boolean;
  isLoading: boolean;
  rawQuery: string;
  groupFilter: number | null;
  selectedIndex: number;
  setQuery: (raw: string) => void;
  setGroupFilter: (groupId: number | null) => void;
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
  remove: (id: number) => Promise<void>;
  togglePinned: (id: number) => Promise<void>;
  moveSelection: (delta: number) => void;
  setSelectedIndex: (index: number) => void;
}

export const useHistory = create<HistoryState>((set, get) => ({
  items: [],
  page: 0,
  hasMore: true,
  isLoading: false,
  rawQuery: "",
  groupFilter: null,
  selectedIndex: 0,

  // Toda digitação reseta a paginação para a página 0 (spec §4).
  setQuery: (raw) => {
    set({ rawQuery: raw, page: 0, hasMore: true });
    void get().refresh();
  },

  setGroupFilter: (groupId) => {
    set({ groupFilter: groupId, page: 0, hasMore: true });
    void get().refresh();
  },

  refresh: async () => {
    const { rawQuery, groupFilter } = get();
    const { search, typeFilter } = parseQuery(rawQuery);
    set({ isLoading: true });
    try {
      const result = await getHistory(0, search, typeFilter, groupFilter ?? undefined);
      set({ items: result.items, page: 1, hasMore: result.hasMore, selectedIndex: 0 });
    } finally {
      set({ isLoading: false });
    }
  },

  // Próxima página; a flag isLoading bloqueia requisições concorrentes (debounce).
  loadMore: async () => {
    const { isLoading, hasMore, page, rawQuery, groupFilter } = get();
    if (isLoading || !hasMore) return;
    const { search, typeFilter } = parseQuery(rawQuery);
    set({ isLoading: true });
    try {
      const result = await getHistory(page, search, typeFilter, groupFilter ?? undefined);
      set((state) => ({
        items: [...state.items, ...result.items],
        page: state.page + 1,
        hasMore: result.hasMore,
      }));
    } finally {
      set({ isLoading: false });
    }
  },

  remove: async (id) => {
    await deleteItem(id);
    set((state) => ({ items: state.items.filter((i) => i.id !== id) }));
  },

  togglePinned: async (id) => {
    const pinned = await togglePin(id);
    set((state) => ({
      items: state.items
        .map((i) => (i.id === id ? { ...i, pinned } : i))
        .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.timestamp - a.timestamp),
    }));
  },

  // Navegação por setas (↑/↓) na lista, com clamp nos limites.
  moveSelection: (delta) => {
    set((state) => {
      if (state.items.length === 0) return state;
      const next = Math.min(Math.max(state.selectedIndex + delta, 0), state.items.length - 1);
      return { selectedIndex: next };
    });
  },

  setSelectedIndex: (index) => set({ selectedIndex: index }),
}));
