import { spring } from "remotion";
import { describe, expect, it } from "vitest";
import { uiSpring } from "../theme/motion";
import { barShareAt, evalLabel, whipSpring, winPct, type BarBeat, type BarPly } from "./winprob";

const cp = (v: number) => ({ cp: v, mate: null });
const mate = (v: number) => ({ cp: null, mate: v });

describe("winPct", () => {
  it("monotonic in cp", () => {
    let last = -1;
    for (let v = -2000; v <= 2000; v += 25) {
      const w = winPct(cp(v));
      expect(w).toBeGreaterThan(last);
      last = w;
    }
  });

  it("clamped 0..100 for cp +-100000", () => {
    for (const v of [100000, -100000, 10000, -10000]) {
      const w = winPct(cp(v));
      expect(w).toBeGreaterThanOrEqual(0);
      expect(w).toBeLessThanOrEqual(100);
      expect(Number.isNaN(w)).toBe(false);
    }
    expect(winPct(cp(100000))).toBeCloseTo(100, 6);
    expect(winPct(cp(-100000))).toBeCloseTo(0, 6);
  });

  it("mate signs", () => {
    expect(winPct(mate(3))).toBe(100);
    expect(winPct(mate(-3))).toBe(0);
  });

  it("symmetric", () => {
    for (const v of [10, 80, 250, 900]) expect(winPct(cp(v)) + winPct(cp(-v))).toBeCloseTo(100, 10);
  });

  it("matches the Python curve at known points", () => {
    expect(winPct(cp(100))).toBeCloseTo(50 + 50 * (2 / (1 + Math.exp(-0.368208)) - 1), 10);
  });

  it("no NaN for {cp: 0}", () => {
    expect(winPct(cp(0))).toBe(50);
  });
});

describe("evalLabel", () => {
  it("labels", () => {
    expect(evalLabel(cp(140))).toBe("+1.4");
    expect(evalLabel(cp(-30))).toBe("\u22120.3");
    expect(evalLabel(cp(0))).toBe("0.0");
    expect(evalLabel(cp(4))).toBe("0.0");
    expect(evalLabel(mate(3))).toBe("M3");
    expect(evalLabel(mate(-3))).toBe("\u2212M3");
  });
});

describe("barShareAt", () => {
  const plies: BarPly[] = [
    { ply: 1, show_at_ms: 1000, eval: cp(0), class: "good" },
    { ply: 2, show_at_ms: 3000, eval: cp(-900), class: "blunder" },
  ];
  const FPS = 30;
  it("holds the previous value, then settles on the new one without overshoot", () => {
    expect(barShareAt(0, FPS, plies, [])).toBe(50);
    expect(barShareAt(90, FPS, plies, [])).toBe(50); // ply 2 not started (frame 90 = 3000 ms)
    let max = -1;
    let min = 101;
    for (let f = 90; f < 200; f++) {
      const s = barShareAt(f, FPS, plies, []);
      max = Math.max(max, s);
      min = Math.min(min, s);
      expect(s).toBeGreaterThanOrEqual(0);
      expect(s).toBeLessThanOrEqual(100);
    }
    expect(max).toBeLessThanOrEqual(50 + 1e-9);
    expect(min).toBeGreaterThanOrEqual(winPct(cp(-900)) - 0.05);
    expect(barShareAt(400, FPS, plies, [])).toBeCloseTo(winPct(cp(-900)), 3);
  });

  it("whips faster on a blunder beat", () => {
    const beats: BarBeat[] = [{ type: "blunder", ply: 2 }];
    const normal = barShareAt(95, FPS, plies, []);
    const whip = barShareAt(95, FPS, plies, beats);
    expect(whip).toBeLessThan(normal); // closer to the new low value
  });

  it("whip spring has no overshoot", () => {
    let max = 0;
    for (let f = 0; f < 60; f++) max = Math.max(max, spring({ frame: f, fps: 30, config: whipSpring }));
    expect(max).toBeLessThanOrEqual(1.0005);
    expect(whipSpring.stiffness).toBe(uiSpring.stiffness! * 3);
  });
});
