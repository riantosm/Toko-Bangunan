import { describe, expect, it } from "vitest";

import { parseCursor } from "./orders";

describe("parseCursor", () => {
  it("returns undefined for missing / empty input", () => {
    expect(parseCursor(undefined)).toBeUndefined();
    expect(parseCursor("")).toBeUndefined();
  });

  it("returns undefined for junk or non-positive values", () => {
    expect(parseCursor("abc")).toBeUndefined();
    expect(parseCursor("0")).toBeUndefined();
    expect(parseCursor("-5")).toBeUndefined();
    expect(parseCursor("12.5")).toBeUndefined();
  });

  it("parses a valid positive integer id", () => {
    expect(parseCursor("61")).toBe(61);
  });
});
