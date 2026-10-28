import { describe, expect, it } from "vitest";
import { blipFrames, typedText } from "./speech";

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

  it("types at about 12 characters per second", () => {
    // 1 s in: about 12 characters have been typed, rounded down to words.
    const out = typedText(EN, 100 + FPS, 100, FPS);
    expect(out.length).toBeGreaterThan(0);
    expect(out.length).toBeLessThanOrEqual(12);
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
        expect(b.frame).toBeGreaterThan(309);
      }
    }
  });

  it("is seeded: another beat gets another sequence", () => {
    expect(blipFrames(EN, 0, FPS, "a").map((b) => b.sample)).not.toEqual(blipFrames(EN, 0, FPS, "b").map((b) => b.sample));
  });
});
