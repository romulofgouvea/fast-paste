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
    const setViewMode = vi.fn();
    // @ts-expect-error Mocking zustand
    useUi.mockImplementation((selector: any) => {
      const state = { viewMode: "modo1", setViewMode };
      return selector(state);
    });

    render(<Header />);
    expect(screen.getByText("FPaste")).toBeDefined();
    
    const modeBtn = screen.getByText("Modo 1");
    fireEvent.click(modeBtn);
    expect(setViewMode).toHaveBeenCalledWith("modo2");
  });

  it("should close window on click close button", () => {
    // @ts-expect-error Mocking zustand
    useUi.mockImplementation((selector: any) => {
      const state = { viewMode: "modo1", setViewMode: vi.fn() };
      return selector(state);
    });

    render(<Header />);
    const closeBtn = screen.getByTitle("Fechar (Esc)");
    fireEvent.click(closeBtn);
    expect(hideWindow).toHaveBeenCalled();
  });
});
