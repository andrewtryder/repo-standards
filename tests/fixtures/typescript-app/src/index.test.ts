import { describe, expect, it } from "vitest";
import { greet } from "./index.js";

describe("greet", () => {
  it("uses default name", () => {
    expect(greet()).toBe("hello world");
  });

  it("uses provided name", () => {
    expect(greet("fixture")).toBe("hello fixture");
  });
});
