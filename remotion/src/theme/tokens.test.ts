import { spring } from "remotion";
import { describe, expect, it } from "vitest";
import { BoardTheme } from "../spec/schema";
import { boardThemes } from "./boardThemes";
import { fontFor } from "./fonts";
import { uiSpring } from "./motion";
import { contrast, tokens } from "./tokens";

describe("tokens", () => {
  it("every text/background pair has contrast >= 4.5", () => {
    const { color } = tokens;
    const text = [color.text, color.muted];
    const grounds = [color.bg, color.surface];
    for (const t of text) for (const g of grounds) expect(contrast(t, g)).toBeGreaterThanOrEqual(4.5);
    // semantic move-quality colors are used as text/marks on the page background
    for (const s of [color.best, color.brilliant, color.mistake, color.blunder])
      expect(contrast(s, color.bg)).toBeGreaterThanOrEqual(4.5);
  });

  it("space is an 8 px grid and size.min is 28", () => {
    expect(tokens.space(3)).toBe(24);
    expect(tokens.size.min).toBe(28);
  });

  it("boardThemes covers all four BoardTheme values", () => {
    expect(Object.keys(boardThemes).sort()).toEqual([...BoardTheme.options].sort());
    expect(boardThemes.bone_slate.light).toBe("#E8E2D4");
    expect(boardThemes.bone_slate.dark).toBe("#6E7F86");
  });

  it("coordinates are legible on both square colors of every theme", () => {
    for (const t of Object.values(boardThemes)) {
      expect(contrast(t.coord, t.light)).toBeGreaterThanOrEqual(4.5);
      expect(contrast(t.coord, t.dark)).toBeGreaterThanOrEqual(4.5);
    }
  });

  it('fontFor("hi","ui") includes "IBM Plex Sans Devanagari"', () => {
    expect(fontFor("hi", "ui")).toContain("IBM Plex Sans Devanagari");
    expect(fontFor("en", "title")).toContain("IBM Plex Sans Condensed");
    expect(fontFor("en", "mono")).toContain("IBM Plex Mono");
  });

  it("spring has no overshoot", () => {
    let max = 0;
    for (let frame = 0; frame < 60; frame++)
      max = Math.max(max, spring({ frame, fps: 30, config: uiSpring }));
    expect(max).toBeLessThanOrEqual(1.0005);
  });
});
