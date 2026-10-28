import type { CSSProperties } from "react";
import { motion } from "../theme/motion";

const EXIT_MS = 240;
const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

/** Enter (uiEnterMs, enter easing) and exit (240 ms, exit easing) of a card shown from startMs to endMs; slides 16 px in from the left. */
export const plateStyle = (nowMs: number, startMs: number, endMs: number): CSSProperties => {
  const e = motion.enter(clamp01((nowMs - startMs) / motion.uiEnterMs));
  const x = motion.exit(clamp01((nowMs - (endMs - EXIT_MS)) / EXIT_MS));
  return { opacity: e * (1 - x), transform: `translateX(${(1 - e) * -16 + x * -8}px)` };
};
