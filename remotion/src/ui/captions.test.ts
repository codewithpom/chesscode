import { describe, expect, it } from "vitest";
import type { NarrationSegment } from "../spec/schema";
import { captionPages, toCaptions } from "./captions";

const seg = (id: string, start: number, words: string[], step = 300): NarrationSegment => ({
  segment_id: id,
  kind: "ply",
  ply: 1,
  text: words.join(" "),
  audio: `audio/${id}.mp3`,
  start_ms: start,
  duration_ms: words.length * step,
  words: words.map((w, i) => ({ w, start_ms: start + i * step, end_ms: start + i * step + step - 40 })),
});

const EN = [
  seg("s1", 1000, "And there it is the knight walks straight into a fork".split(" ")),
  seg("s2", 8000, "Black resigns three moves later because nothing can be saved".split(" ")),
];
const HI = [
  seg("h1", 500, ["क्षमा", "कीजिए,", "वज़ीर", "पड़ा", "रहा", "ज़्यादा", "देर", "तक"]),
  seg("h2", 6000, ["यह", "चाल", "बहुत", "क्षति", "पहुँचाती", "है"]),
];
const wordsOf = (n: NarrationSegment[]) => n.flatMap((s) => s.words.map((w) => w.w));
const pageWords = (pages: ReturnType<typeof captionPages>) =>
  pages.flatMap((p) => p.tokens.map((t) => t.text.trim()));

describe("toCaptions", () => {
  it("every token text starts with a space", () => {
    for (const n of [EN, HI]) {
      const caps = toCaptions(n);
      expect(caps).toHaveLength(wordsOf(n).length);
      caps.forEach((c, i) => {
        expect(c.text).toBe(" " + wordsOf(n)[i]);
        expect(c).toMatchObject({ timestampMs: null, confidence: null });
      });
    }
    // createTikTokStyleCaptions trims the first token of each page; every later token keeps its space.
    for (const mode of ["long", "shorts"] as const)
      for (const p of captionPages(EN, mode)) {
        expect(p.tokens[0].text.startsWith(" ")).toBe(false);
        for (const t of p.tokens.slice(1)) expect(t.text.startsWith(" ")).toBe(true);
      }
  });
});

describe("captionPages", () => {
  it("pages never split a word (EN and Hindi, incl. क्षमा, पड़ा, ज़्यादा)", () => {
    for (const n of [EN, HI])
      for (const mode of ["long", "shorts"] as const) {
        const pages = captionPages(n, mode);
        expect(pageWords(pages)).toEqual(wordsOf(n));
        for (const p of pages) expect(p.tokens.map((t) => t.text).join("")).toBe(p.text);
      }
    const all = captionPages(HI, "long").flatMap((p) => p.tokens.map((t) => t.text.trim()));
    for (const w of ["क्षमा", "पड़ा", "ज़्यादा"]) expect(all).toContain(w);
  });

  it("shorts pages have 1 to 3 words, even for fast speech", () => {
    const fast = [seg("f", 0, "a b c d e f g h i j k l".split(" "), 100)];
    for (const n of [EN, HI, fast])
      for (const p of captionPages(n, "shorts")) {
        expect(p.tokens.length).toBeGreaterThanOrEqual(1);
        expect(p.tokens.length).toBeLessThanOrEqual(3);
      }
  });

  it("long-form pages combine words (fewer pages than words)", () => {
    expect(captionPages(EN, "long").length).toBeLessThan(wordsOf(EN).length);
  });

  it("page timing within its segment", () => {
    for (const n of [EN, HI])
      for (const mode of ["long", "shorts"] as const)
        for (const p of captionPages(n, mode)) {
          const owner = n.find((s) => p.tokens[0].fromMs >= s.words[0].start_ms && p.tokens[0].fromMs <= s.words[s.words.length - 1].end_ms)!;
          expect(owner).toBeDefined();
          expect(p.startMs).toBe(p.tokens[0].fromMs);
          for (const t of p.tokens) {
            expect(t.fromMs).toBeGreaterThanOrEqual(owner.words[0].start_ms);
            expect(t.toMs).toBeLessThanOrEqual(owner.words[owner.words.length - 1].end_ms);
          }
        }
  });
});
