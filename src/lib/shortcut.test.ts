import { describe, it, expect } from "vitest";
import {
  eventToShortcut,
  displayShortcut,
  isModifierKey,
  currentModifiers,
} from "./shortcut";

function kbd(init: Partial<KeyboardEvent>): KeyboardEvent {
  return {
    key: "",
    code: "",
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    shiftKey: false,
    ...init,
  } as KeyboardEvent;
}

describe("shortcut", () => {
  it("eventToShortcut exige ao menos um modificador", () => {
    expect(eventToShortcut(kbd({ code: "KeyA" }))).toBeNull();
  });

  it("eventToShortcut monta combinações válidas", () => {
    expect(eventToShortcut(kbd({ ctrlKey: true, code: "KeyK" }))).toBe("CommandOrControl+K");
    expect(eventToShortcut(kbd({ ctrlKey: true, shiftKey: true, code: "Digit1" }))).toBe(
      "CommandOrControl+Shift+1",
    );
    expect(eventToShortcut(kbd({ altKey: true, code: "Quote" }))).toBe("Alt+Quote");
  });

  it("eventToShortcut rejeita teclas não suportadas", () => {
    expect(eventToShortcut(kbd({ ctrlKey: true, code: "CapsLock" }))).toBeNull();
  });

  it("displayShortcut formata para humanos", () => {
    expect(displayShortcut("CommandOrControl+Quote")).toBe("Ctrl + '");
    expect(displayShortcut("Alt+Shift+Up")).toBe("Alt + Shift + ↑");
  });

  it("isModifierKey e currentModifiers", () => {
    expect(isModifierKey(kbd({ key: "Control" }))).toBe(true);
    expect(isModifierKey(kbd({ key: "a" }))).toBe(false);
    expect(currentModifiers(kbd({ ctrlKey: true, shiftKey: true }))).toEqual([
      "CommandOrControl",
      "Shift",
    ]);
  });
});
