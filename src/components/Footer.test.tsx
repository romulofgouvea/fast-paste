import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Footer } from "./Footer";
import { useHistory } from "../stores/history";

vi.mock("../stores/history", () => ({
  useHistory: vi.fn(),
}));

vi.mock("../stores/ui", () => ({
  useUi: vi.fn(() => false), // viewMode
}));

describe("Footer", () => {
  it("should render settings button and handle click", () => {
    // @ts-expect-error Mocking zustand
    useHistory.mockImplementation((selector: any) => {
      const state = { groupFilter: null, setGroupFilter: vi.fn() };
      return selector(state);
    });

    const fakeHelper = vi.fn().mockResolvedValue(undefined);
    (window as any).__fpasteOpenSettings = fakeHelper;

    render(<Footer />);
    
    const btn = screen.getByText("Config");
    expect(btn).toBeDefined();
    
    fireEvent.click(btn);
    expect(fakeHelper).toHaveBeenCalled();
  });
});
