import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ItemCard } from "./ItemCard";
import type { ClipItem } from "../lib/api";

describe("ItemCard", () => {
  const mockItem: ClipItem = {
    id: 1,
    type: "text",
    content: "hello world\nline 2",
    timestamp: Date.now(),
    pinned: false,
    groupId: null,
    preview: null,
    hasMedia: false,
  };

  it("should render title and text badge", () => {
    const onSelect = vi.fn();
    render(<ItemCard item={mockItem} selected={false} onSelect={onSelect} onDelete={vi.fn()} onTogglePin={vi.fn()} />);

    // O título é a primeira linha não vazia do conteúdo.
    expect(screen.getByText("hello world")).toBeDefined();
    // O badge exibe o rótulo do tipo ("Texto"); o maiúsculo é só CSS (uppercase).
    expect(screen.getByText("Texto")).toBeDefined();
  });

  it("should trigger onSelect on click", () => {
    const onSelect = vi.fn();
    render(<ItemCard item={mockItem} selected={false} onSelect={onSelect} onDelete={vi.fn()} onTogglePin={vi.fn()} />);

    // O cartão é o botão cujo nome acessível contém o título do item.
    const card = screen.getByRole("button", { name: /hello world/i });
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledWith(1);
  });
});
