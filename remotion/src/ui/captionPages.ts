import { createTikTokStyleCaptions, type Caption, type TikTokPage, type TikTokToken } from "@remotion/captions";
import type { NarrationSegment } from "../spec/schema";

const COMBINE_MS = { long: 1200, shorts: 400 } as const;
const SHORTS_MAX_WORDS = 3;
// Clause-ending punctuation: . , ? ! and the Devanagari danda.
const CLAUSE_END = /[.,?!\u0964]$/;

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

/** Splits a segment at clause-ending punctuation; a one-word clause joins the next clause. */
const clauses = (captions: Caption[]): Caption[][] => {
  const raw: Caption[][] = [];
  let cur: Caption[] = [];
  for (const c of captions) {
    cur.push(c);
    if (CLAUSE_END.test(c.text.trim())) {
      raw.push(cur);
      cur = [];
    }
  }
  if (cur.length) raw.push(cur);

  const out: Caption[][] = [];
  let carry: Caption[] = [];
  for (const c of raw) {
    const merged = carry.concat(c);
    if (merged.length === 1) carry = merged;
    else {
      out.push(merged);
      carry = [];
    }
  }
  // A trailing one-word clause stays its own clause; captionPages lets it borrow a word from the page before.
  if (carry.length) out.push(carry);
  return out;
};

// Same convention as the library: the first token of a page has no leading space.
const makePage = (tokens: TikTokToken[]): TikTokPage => {
  const fixed = tokens.map((t, j) => ({ ...t, text: j === 0 ? t.text.trimStart() : " " + t.text.trimStart() }));
  return {
    text: fixed.map((t) => t.text).join(""),
    startMs: fixed[0].fromMs,
    tokens: fixed,
    durationMs: fixed[fixed.length - 1].toMs - fixed[0].fromMs,
  };
};

/** Splits n tokens into ceil(n / max) near-equal pages (7 -> 3,2,2), so there is never a 1-word tail. */
const balanced = (tokens: TikTokToken[], max: number): TikTokToken[][] => {
  const k = Math.ceil(tokens.length / max);
  const base = Math.floor(tokens.length / k);
  const extra = tokens.length % k;
  const out: TikTokToken[][] = [];
  let at = 0;
  for (let i = 0; i < k; i++) {
    const size = base + (i < extra ? 1 : 0);
    out.push(tokens.slice(at, at + size));
    at += size;
  }
  return out;
};

/**
 * Pages never cross a narration segment and end at clause punctuation when one falls inside the page;
 * whole words only, so Devanagari clusters are never split; a page is never a lone word when it can
 * borrow from the previous page of the same clause.
 */
export const captionPages = (narration: NarrationSegment[], mode: "long" | "shorts"): TikTokPage[] => {
  const captions = narration.flatMap((s) =>
    clauses(toCaptions([s])).flatMap((clause) => {
      return clause.map((c, i) => (i === clause.length - 1 ? { ...c, pageBreakAfter: true } : c));
    }),
  );
  const { pages } = createTikTokStyleCaptions({
    captions,
    combineTokensWithinMilliseconds: COMBINE_MS[mode],
  });

  let groups: TikTokToken[][] = pages.map((p) => p.tokens);
  if (mode === "shorts") groups = groups.flatMap((g) => (g.length > SHORTS_MAX_WORDS ? balanced(g, SHORTS_MAX_WORDS) : [g]));

  // Fix lone-word pages: borrow the previous page's last word (so "fork! Ouch." travel together),
  // or join a short previous page (a one-word sentence then trails a punctuation mark inside the page).
  const max = mode === "shorts" ? SHORTS_MAX_WORDS : Infinity;
  const fixed: TikTokToken[][] = [];
  for (const g of groups) {
    const prev = fixed[fixed.length - 1];
    if (g.length === 1 && prev && prev.length >= 3) fixed.push([prev.pop()!, ...g]);
    else if (g.length === 1 && prev && prev.length + 1 <= max) prev.push(...g);
    else fixed.push(g);
  }
  return fixed.map(makePage);
};
