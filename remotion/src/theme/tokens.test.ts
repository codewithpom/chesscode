import { spring } from "remotion";
import { describe, expect, it } from "vitest";
import { BoardTheme } from "../spec/schema";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { boardThemes, pieceBlack, pieceBlackInk } from "./boardThemes";
import { fontFor } from "./fonts";
import { uiSpring } from "./motion";
import { contrast, hue, tokens } from "./tokens";

describe("tokens", () => {
  it("every text/background pair has contrast >= 4.5", () => {
    const { color } = tokens;
    const text = [color.text, color.muted];
    const grounds = [color.bg, color.surface];
    for (const t of text) for (const g of grounds) expect(contrast(t, g)).toBeGreaterThanOrEqual(4.5);
    // semantic move-quality and threat colors are used as text/marks on both grounds
    for (const s of [color.best, color.brilliant, color.mistake, color.blunder, color.threat])
      for (const g of grounds) expect(contrast(s, g)).toBeGreaterThanOrEqual(4.5);
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

  it("threat is its own token and the eval bar has a dark share token", () => {
    expect(Object.keys(tokens.color)).toContain("threat");
    expect(tokens.color.evalBlack).toBe("#3A3F4A");
  });

  it("last-move tints are opaque per-theme hex colors, distinct from the squares", () => {
    const hex = /^#[0-9A-F]{6}$/i;
    for (const t of Object.values(boardThemes)) {
      expect(t.lastMoveLight).toMatch(hex);
      expect(t.lastMoveDark).toMatch(hex);
      expect(t.lastMoveLight).not.toBe(t.light);
      expect(t.lastMoveDark).not.toBe(t.dark);
    }
    expect(boardThemes.bone_slate.lastMoveLight).toBe("#DCD3B0");
    expect(boardThemes.bone_slate.lastMoveDark).toBe("#8E9A8C");
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

  it("black pieces have >= 3:1 against every theme's dark and light squares (and last-move tints)", () => {
    for (const [name, t] of Object.entries(boardThemes))
      for (const sq of [t.light, t.dark, t.lastMoveLight, t.lastMoveDark])
        expect(contrast(pieceBlack, sq), `${name} ${sq}`).toBeGreaterThanOrEqual(3);
  });

  it("black piece SVGs use the recolor (fill and light ink), not the original terracotta", () => {
    for (const t of ["K", "Q", "R", "B", "N", "P"]) {
      const svg = readFileSync(resolve(__dirname, `../assets/pieces/b${t}.svg`), "utf8").toLowerCase();
      expect(svg).toContain(pieceBlack.toLowerCase());
      expect(svg).toContain(pieceBlackInk.toLowerCase());
      expect(svg).not.toContain("#d1774b");
    }
  });

  it("themes: every pair differs in dark-square hue by >= 25 degrees", () => {
    const names = Object.keys(boardThemes) as Array<keyof typeof boardThemes>;
    for (let i = 0; i < names.length; i++)
      for (let j = i + 1; j < names.length; j++) {
        const d = Math.abs(hue(boardThemes[names[i]].dark) - hue(boardThemes[names[j]].dark));
        expect(Math.min(d, 360 - d), `${names[i]} vs ${names[j]}`).toBeGreaterThanOrEqual(25);
      }
  });

  it("themes: light/dark square contrast stays near 3.0 to 3.25", () => {
    for (const [name, t] of Object.entries(boardThemes)) {
      const c = contrast(t.light, t.dark);
      expect(c, name).toBeGreaterThanOrEqual(3.0);
      expect(c, name).toBeLessThanOrEqual(3.25);
    }
  });
});
