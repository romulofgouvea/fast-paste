import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Settings from "./Settings";

// Mock Tauri APIs
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue(null),
}));

vi.mock("@tauri-apps/api/event", () => ({
  emit: vi.fn().mockResolvedValue(null),
  listen: vi.fn().mockResolvedValue(() => {}),
}));

vi.mock("@tauri-apps/plugin-store", () => ({
  load: vi.fn().mockResolvedValue({
    get: vi.fn().mockResolvedValue(null),
    set: vi.fn(),
    save: vi.fn(),
  }),
}));

describe("Settings Window", () => {
  it("should render without crashing", () => {
    render(<Settings />);
    
    // As abas principais do menu devem existir
    expect(screen.getByText("Aparência")).toBeDefined();
    expect(screen.getByText("Atalhos")).toBeDefined();
    expect(screen.getByText("Armazenamento")).toBeDefined();
    expect(screen.getByText("Backup")).toBeDefined();

    // Como AppearanceTab é carregado por default, o título "Modo de Tema" deve estar visível
    expect(screen.getByText("Modo de Tema")).toBeDefined();
  });
});
