import { describe, it, expect } from "vitest";
import { invertCase, removeLineBreaks, asPlainText } from "./transform";

describe("transform", () => {
  it("invertCase troca a caixa caractere a caractere", () => {
    expect(invertCase("Hello World")).toBe("hELLO wORLD");
    expect(invertCase("abc123")).toBe("ABC123");
  });

  it("removeLineBreaks colapsa quebras em um único espaço e apara as pontas", () => {
    expect(removeLineBreaks("a\nb\n\nc")).toBe("a b c");
    expect(removeLineBreaks("  line1 \r\n line2  ")).toBe("line1 line2");
  });

  it("asPlainText remove caracteres de controle mas preserva quebras e apara", () => {
    const withControls = `a${String.fromCharCode(0)}b${String.fromCharCode(7)}c`;
    expect(asPlainText(withControls)).toBe("abc");
    expect(asPlainText("  hi  ")).toBe("hi");
    expect(asPlainText("a\nb")).toBe("a\nb");
  });
});
