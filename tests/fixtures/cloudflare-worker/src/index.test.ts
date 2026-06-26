import { describe, expect, it } from "vitest";
import { greet } from "./index.js";

describe("greet", () => {
  it("returns worker greeting", () => {
    expect(greet("worker")).toBe("hello worker");
  });
});
