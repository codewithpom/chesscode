import type { Box } from "../theme/layout";
import { RIG } from "./Pyaada";
import { BUBBLE_FONT, BUBBLE_TAIL } from "./speech";

const GAP = 8;
const MAX_BUBBLE_W = 580;
const MAX_BUBBLE_H = 200;

export const mascotWidth = (height: number): number => (height * RIG.w) / RIG.h;

/** Mascot bottom-right in `box`, bubble to its left. Both rects are inside `box` by construction. */
export const layerRects = (box: Box, height: number): { mascot: Box; bubble: Box } => {
  const w = mascotWidth(height);
  const mascot = { x: box.x + box.w - w, y: box.y + box.h - height, w, h: height };
  const bw = Math.min(MAX_BUBBLE_W, box.w - w - GAP);
  const bh = Math.min(box.h, MAX_BUBBLE_H);
  // Centred on the mouth (about 48% down the rig) so the tail points at it, kept inside the box.
  const mouthY = mascot.y + height * 0.48;
  const by = Math.min(box.y + box.h - bh, Math.max(box.y, mouthY - bh / 2));
  return { mascot, bubble: { x: mascot.x - GAP - bw, y: by, w: bw, h: bh } };
};

/** Lines a text needs in a bubble of width `w` (estimate: wide average glyph so it errs on the safe side). */
export const estimateLines = (line: string, w: number): number => {
  const inner = w - BUBBLE_TAIL - 2 * 24 - 2 * 4;
  const perLine = Math.max(1, Math.floor(inner / (BUBBLE_FONT * 0.6)));
  let lines = 1;
  let used = 0;
  for (const word of line.split(" ")) {
    const len = [...word].length;
    if (used > 0 && used + 1 + len > perLine) {
      lines++;
      used = len;
    } else used += (used > 0 ? 1 : 0) + len;
  }
  return lines;
};

/** Height the text needs: lines at 1.3 line height plus the bubble padding and border. */
export const textHeight = (lines: number): number => lines * BUBBLE_FONT * 1.3 + 2 * 16 + 2 * 4;
