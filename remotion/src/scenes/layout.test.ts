import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { fxWindows } from "../fx/windows";
import { studioLayout, type Box } from "../theme/layout";
import { sceneRanges } from "./timeline";

const spec = VideoSpec.parse(
  JSON.parse(readFileSync(resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"), "utf8")),
);
const FPS = 30;
const b = studioLayout.boxes;
const hit = (p: Box, q: Box): boolean => p.x < q.x + q.w && q.x < p.x + p.w && p.y < q.y + q.h && q.y < p.y + p.h;

// What each scene draws, by name. The board column is the same in every scene that has a board.
const boardColumn = { board: b.board, evalBar: b.evalBar, evalLabel: b.evalLabel, rankLabels: b.rankLabels, fileLabels: b.fileLabels };
const shown: Record<string, Record<string, Box>> = {
  playback: { label: b.label, cards: b.cards, moveList: b.moveList, bubble: b.bubble, mascot: b.mascot, captions: b.captions },
  cold_open: { hook: b.hook, bubble: b.bubble, mascot: b.mascot, captions: b.captions },
  key_moment: { label: b.label, bubble: b.bubble, mascot: b.mascot, captions: b.captions },
  outro: { outroMascot: b.outroMascot },
};

/** Every frame the layout must hold at: the beat's own frame, when its mascot line appears (frame 10), and each fx window start. */
const beatFrames = (s: VideoSpec): number[] => {
  const frames = new Set<number>();
  for (const beat of s.beats) {
    const at = msToFrame(beat.at_ms, FPS);
    frames.add(at);
    frames.add(at + 10);
  }
  for (const w of fxWindows(s.beats, FPS)) frames.add(w.from);
  return [...frames];
};

describe("Studio layout at every beat frame of the fixture", () => {
  const ranges = sceneRanges(spec);
  const frames = beatFrames(spec);

  it("has beat frames to check", () => expect(frames.length).toBeGreaterThanOrEqual(4));

  it.each(frames)("frame %i: mascot, bubble, captions, move list and labels clear the board and eval bar and each other", (frame) => {
    const ms = (frame * 1000) / FPS;
    const scene = ranges.find((r) => ms >= r.startMs && ms < r.endMs)!;
    const boxes = shown[scene.kind] ?? {};
    const names = Object.keys(boxes);
    for (const n of names) {
      if (scene.kind !== "outro") for (const [bn, bb] of Object.entries(boardColumn)) expect(hit(boxes[n], bb), `${n} vs ${bn}`).toBe(false);
    }
    for (let i = 0; i < names.length; i++)
      for (let j = i + 1; j < names.length; j++) expect(hit(boxes[names[i]], boxes[names[j]]), `${names[i]} vs ${names[j]}`).toBe(false);
  });

  it("every scene's boxes avoid each other and the board column, whatever beats it has", () => {
    for (const [kind, boxes] of Object.entries(shown)) {
      const names = Object.keys(boxes);
      for (let i = 0; i < names.length; i++) {
        if (kind !== "outro") for (const bb of Object.values(boardColumn)) expect(hit(boxes[names[i]], bb), `${kind}: ${names[i]}`).toBe(false);
        for (let j = i + 1; j < names.length; j++) expect(hit(boxes[names[i]], boxes[names[j]]), `${kind}: ${names[i]} vs ${names[j]}`).toBe(false);
      }
    }
  });

  it("follows the spec: 96 px margins, board 800 centred, eval bar 24 px 16 px left of the board", () => {
    const { width, height } = studioLayout;
    expect(b.board).toEqual({ x: 136, y: 140, w: 800, h: 800 });
    expect(b.board.y + b.board.h / 2).toBe(height / 2);
    expect(b.evalBar.x + b.evalBar.w + 16).toBe(b.board.x);
    expect(b.evalBar.w).toBe(24);
    for (const n of ["label", "cards", "moveList", "bubble", "mascot", "captions", "hook"] as const) {
      const bx = b[n];
      expect(bx.x, n).toBeGreaterThanOrEqual(1000);
      expect(bx.x + bx.w, n).toBeLessThanOrEqual(width - 96);
      expect(bx.y, n).toBeGreaterThanOrEqual(96);
      expect(bx.y + bx.h, n).toBeLessThanOrEqual(height - 96);
    }
    expect(b.moveList.h).toBe(studioLayout.moveRows * studioLayout.moveRowHeight);
    expect(b.mascot.h).toBeLessThanOrEqual(200);
    expect(b.outroMascot.x + b.outroMascot.w).toBeLessThanOrEqual(width / 3); // the right two thirds stay empty
  });
});
