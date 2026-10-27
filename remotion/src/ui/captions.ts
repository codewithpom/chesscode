import { createTikTokStyleCaptions, type Caption, type TikTokPage } from "@remotion/captions";
import type { NarrationSegment } from "../spec/schema";

const COMBINE_MS = { long: 1200, shorts: 400 } as const;
const SHORTS_MAX_WORDS = 3;

/** One caption per word. The leading space is the delimiter createTikTokStyleCaptions splits on. */
export const toCaptions = (narration: NarrationSegment[]): Caption[] =>
  narration.flatMap((s) =>
    s.words.map((w) => ({
      text: " " + w.w,
      startMs: w.start_ms,
      endMs: w.end_ms,
      timestampMs: null,
      confidence: null,
    })),
  );

const chunk = (page: TikTokPage, size: number): TikTokPage[] => {
  const out: TikTokPage[] = [];
  for (let i = 0; i < page.tokens.length; i += size) {
    // Same convention as the library: the first token of a page has no leading space.
    const tokens = page.tokens.slice(i, i + size).map((t, j) => (j === 0 ? { ...t, text: t.text.trimStart() } : t));
    out.push({
      text: tokens.map((t) => t.text).join(""),
      startMs: tokens[0].fromMs,
      tokens,
      durationMs: tokens[tokens.length - 1].toMs - tokens[0].fromMs,
    });
  }
  return out;
};

/** Pages never cross a narration segment; whole words only, so Devanagari clusters are never split. */
export const captionPages = (narration: NarrationSegment[], mode: "long" | "shorts"): TikTokPage[] => {
  const captions = narration.flatMap((s) =>
    toCaptions([s]).map((c, i, all) => (i === all.length - 1 ? { ...c, pageBreakAfter: true } : c)),
  );
  const { pages } = createTikTokStyleCaptions({
    captions,
    combineTokensWithinMilliseconds: COMBINE_MS[mode],
  });
  return mode === "shorts" ? pages.flatMap((p) => chunk(p, SHORTS_MAX_WORDS)) : pages;
};
