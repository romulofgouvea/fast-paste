import { describe, it, expect } from "vitest";
import { parseQuery } from "./parseQuery";

describe("parseQuery", () => {
  it("should parse normal search text", () => {
    const result = parseQuery("hello world");
    expect(result.search).toBe("hello world");
    expect(result.typeFilter).toBeUndefined();
  });

  it("should extract type filter and keep rest as search", () => {
    const result = parseQuery("hello tipo:imagem world");
    expect(result.search).toBe("hello world");
    expect(result.typeFilter).toBe("image");
  });

  it("should handle english type filter aliases", () => {
    const result = parseQuery("type:code something");
    expect(result.search).toBe("something");
    expect(result.typeFilter).toBe("code");
  });

  it("should ignore unknown type filters", () => {
    const result = parseQuery("tipo:unknown something");
    expect(result.search).toBe("tipo:unknown something");
    expect(result.typeFilter).toBeUndefined();
  });
});
