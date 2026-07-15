import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";

// A auto-limpeza do Testing Library só se registra quando `afterEach` é global
// (vitest com globals: true). Como os testes importam os helpers explicitamente,
// registramos a limpeza manualmente — sem isso, cada render vaza para o teste
// seguinte e queries como getByTitle/getByRole encontram elementos duplicados.
afterEach(() => {
  cleanup();
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
