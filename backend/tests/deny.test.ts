import { describe, expect, it } from "vitest";
import { isDeniedUserId, parseDeniedUserIds } from "../src/domain/deny.js";

describe("parseDeniedUserIds", () => {
  it("parses comma-separated ids with trim and empty drop", () => {
    expect([...parseDeniedUserIds(" U1 ,U2,, ")]).toEqual(["U1", "U2"]);
  });

  it("returns empty set for blank / undefined", () => {
    expect(parseDeniedUserIds(undefined).size).toBe(0);
    expect(parseDeniedUserIds("").size).toBe(0);
    expect(parseDeniedUserIds("   ").size).toBe(0);
  });
});

describe("isDeniedUserId", () => {
  const denied = parseDeniedUserIds("U1,U2");

  it("returns true for listed ids", () => {
    expect(isDeniedUserId("U1", denied)).toBe(true);
  });

  it("returns false for unknown, empty, or empty set", () => {
    expect(isDeniedUserId("U9", denied)).toBe(false);
    expect(isDeniedUserId("", denied)).toBe(false);
    expect(isDeniedUserId(undefined, denied)).toBe(false);
    expect(isDeniedUserId("U1", new Set())).toBe(false);
  });
});
