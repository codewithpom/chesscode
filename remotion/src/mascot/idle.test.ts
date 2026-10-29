import { describe, expect, it } from "vitest";
import { blinkStarts, idleAt } from "./idle";

const FPS = 30;

describe("idleAt", () => {
  it("is deterministic and seed-dependent", () => {
    expect(idleAt(123, FPS, "a")).toEqual(idleAt(123, FPS, "a"));
    expect(blinkStarts(600, FPS, "a")).not.toEqual(blinkStarts(600, FPS, "b"));
  });

  it("blinks every 2.5 to 5 s over 60 s", () => {
    const starts = blinkStarts(60 * FPS, FPS, "cc-2026-0001-en");
    expect(starts.length).toBeGreaterThan(10);
    for (let i = 1; i < starts.length; i++) {
      const gap = starts[i] - starts[i - 1];
      expect(gap).toBeGreaterThanOrEqual(75);
      expect(gap).toBeLessThanOrEqual(150);
    }
  });

  it("closes the eye on a blink and keeps breath in [1.00, 1.02]", () => {
    const [first] = blinkStarts(600, FPS, "x");
    expect(idleAt(first + 1, FPS, "x").eyeOpen).toBe(0);
    expect(idleAt(first + 4, FPS, "x").eyeOpen).toBe(1);
    for (let f = 0; f < 60 * FPS; f++) {
      const b = idleAt(f, FPS, "x").squash!;
      expect(b).toBeGreaterThanOrEqual(1);
      expect(b).toBeLessThanOrEqual(1.02 + 1e-12);
    }
  });
});
