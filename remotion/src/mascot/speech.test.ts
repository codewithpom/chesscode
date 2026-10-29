import { describe, expect, it } from "vitest";
import { reactionsFor } from "./react";
import { BUBBLE_EXIT_FRAMES, blipFrames, typedText } from "./speech";
import type { Beat } from "../spec/schema";

const FPS = 30;
const EN = "Two pieces. That's all he needed.";
const HI = "यह क्षति त्रुटि नहीं श्रेष्ठ कृपया ज़्यादा blunder है, भाई";

const isWholeWords = (line: string, out: string) => {
  const w = line.split(" ");
  const o = out === "" ? [] : out.split(" ");
  expect(o).toEqual(w.slice(0, o.length));
};

describe("typedText", () => {
  it("never returns a partial word (English and Devanagari conjuncts)", () => {
    for (const line of [EN, HI]) {
      let prev = 0;
      for (let f = 100; f < 100 + 400; f++) {
        const out = typedText(line, f, 100, FPS);
        isWholeWords(line, out);
        expect(out.length).toBeGreaterThanOrEqual(prev);
        prev = out.length;
      }
      expect(typedText(line, 100 + 400, 100, FPS)).toBe(line);
      expect(typedText(line, 99, 100, FPS)).toBe("");
    }
  });

  it("shows the first word on the first frame, then types at about 12 characters per second", () => {
    expect(typedText(EN, 100, 100, FPS)).toBe("Two");
    // 1 s in: only words that start within the first 12 characters are up.
    expect(typedText(EN, 100 + FPS, 100, FPS)).toBe("Two pieces. That's");
    expect(typedText(EN, 100 + FPS - 1, 100, FPS)).toBe("Two pieces.");
  });
});

describe("blipFrames", () => {
  it("has one blip per word and is deterministic", () => {
    for (const line of [EN, HI]) {
      const a = blipFrames(line, 309, FPS, "cc-1-b-01");
      expect(a).toHaveLength(line.split(" ").length);
      expect(a).toEqual(blipFrames(line, 309, FPS, "cc-1-b-01"));
      for (const b of a) {
        expect(b.sample).toBeGreaterThanOrEqual(1);
        expect(b.sample).toBeLessThanOrEqual(6);
        expect(b.frame).toBeGreaterThanOrEqual(309);
      }
    }
  });

  it("is seeded: another beat gets another sequence", () => {
    expect(blipFrames(EN, 0, FPS, "a").map((b) => b.sample)).not.toEqual(blipFrames(EN, 0, FPS, "b").map((b) => b.sample));
  });
});

describe("long lines inside the bubble lifetime", () => {
  const LONG = "Congratulations, your spectacular strategy accidentally promoted the opponent.";
  const beat: Beat = {
    beat_id: "b", type: "blunder", ply: 1, at_ms: 1000, intensity: 1, mascot: { pose: "side_eye", line: LONG }, fx: [], sfx: null,
  };

  it("shows every word and plays every blip before the exit starts", () => {
    const [r] = reactionsFor([beat], FPS, 3000);
    const lastFull = r.bubbleTo - BUBBLE_EXIT_FRAMES - 1;
    expect(typedText(LONG, r.bubbleFrom, r.bubbleFrom, FPS, r.bubbleTo)).toBe("Congratulations,");
    expect(typedText(LONG, lastFull, r.bubbleFrom, FPS, r.bubbleTo)).toBe(LONG);
    const blips = blipFrames(LONG, r.bubbleFrom, FPS, "s", r.bubbleTo);
    expect(blips).toHaveLength(LONG.split(" ").length);
    for (const b of blips) expect(b.frame).toBeLessThanOrEqual(lastFull);
    expect(blips[0].frame).toBe(r.bubbleFrom);
  });

  it("keeps the normal speed when the bubble is long enough", () => {
    const [r] = reactionsFor([{ ...beat, mascot: { pose: "side_eye", line: EN } }], FPS, 3000);
    expect(typedText(EN, r.bubbleFrom + FPS, r.bubbleFrom, FPS, r.bubbleTo)).toBe(typedText(EN, r.bubbleFrom + FPS, r.bubbleFrom, FPS));
  });
});
