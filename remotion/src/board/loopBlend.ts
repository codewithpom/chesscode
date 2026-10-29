import { motion } from "../theme/motion";
import type { BoardPiece, BoardState } from "./boardState";

const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

/** Progress 0..1 of the closing ease: 0 before the last `n` frames, exactly 1 on the very last frame. */
export const loopProgress = (frame: number, total: number, n = 10): number => clamp01((frame - (total - n)) / (n - 1));

/**
 * Pieces eased from the final position `end` back to the opening position `start` (t 0..1, enter easing), so the
 * last frame of a Short is the first frame. A piece in both slides back; one only in `end` fades out; one only in
 * `start` (a captured piece) fades in; a promoted piece swaps type halfway. Arrows go, highlights switch at the middle.
 */
export const blendStates = (end: BoardState, start: BoardState, t: number): BoardState => {
  const e = motion.enter(clamp01(t));
  const lerp = (a: number, b: number): number => a + (b - a) * e;
  const startById = new Map(start.pieces.map((p) => [p.id, p]));
  const endIds = new Set(end.pieces.map((p) => p.id));
  const pieces: BoardPiece[] = end.pieces.map((p) => {
    const s = startById.get(p.id);
    if (!s) return { ...p, opacity: p.opacity * (1 - e) };
    const from = t < 0.5 ? p : s;
    return { ...p, type: from.type, x: lerp(p.x, s.x), y: lerp(p.y, s.y), opacity: lerp(p.opacity, s.opacity), scale: lerp(p.scale, s.scale) };
  });
  for (const s of start.pieces) if (!endIds.has(s.id)) pieces.push({ ...s, opacity: s.opacity * e });
  return { ply: t < 0.5 ? end.ply : start.ply, pieces, highlights: t < 0.5 ? end.highlights : start.highlights, arrows: [] };
};
