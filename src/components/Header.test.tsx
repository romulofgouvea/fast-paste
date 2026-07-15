import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "./Header";
import { useUi } from "../stores/ui";
import { hideWindow } from "../lib/api";

vi.mock("../stores/ui", () => ({
  useUi: vi.fn(),
}));

vi.mock("../lib/api", () => ({
  hideWindow: vi.fn(),
}));

describe("Header", () => {
  it("should render and toggle viewMode", () => {
    const toggleViewMode = vi.fn();
    // @ts-expect-error Mocking zustand
    useUi.mockImplementation((selector: any) => {
      const state = { viewMode: "modo1", toggleViewMode };
      return selector(state);
    });

    render(<Header />);
    expect(screen.getByText("FPaste")).toBeDefined();

    const modeBtn = screen.getByText("Modo 1");
    fireEvent.click(modeBtn);
    expect(toggleViewMode).toHaveBeenCalled();
  });

  it("should close window on click close button", () => {
    // @ts-expect-error Mocking zustand
    useUi.mockImplementation((selector: any) => {
      const state = { viewMode: "modo1", toggleViewMode: vi.fn() };
      return selector(state);
    });

    render(<Header />);
    const closeBtn = screen.getByTitle("Fechar");
    fireEvent.click(closeBtn);
    expect(hideWindow).toHaveBeenCalled();
  });
});
