import type { Ply } from "../spec/schema";
import { frameToMs, msToFrame } from "../spec/time";
import { motion } from "../theme/motion";
import type { PlacedPiece, PlyState } from "./positions";

export type Highlight = Ply["highlights"][number];
export type Arrow = Ply["arrows"][number];
export type PlyInput = Pick<Ply, "ply" | "show_at_ms" | "arrows" | "highlights">;
export type BoardPiece = PlacedPiece & { x: number; y: number; opacity: number; scale: number };
export type BoardState = { ply: number; pieces: BoardPiece[]; highlights: Highlight[]; arrows: Arrow[] };

const PROMOTION_POP_MS = 160;
const PROMOTION_POP_SCALE = 1.12;
const MAX_ARROWS = 2;

/** Square name to board units from White's view: x 0..7 = a..h, y 0..7 = rank 8..1. */
export const squareXY = (sq: string): { x: number; y: number } => ({
  x: sq.charCodeAt(0) - 97,
  y: 8 - Number(sq[1]),
});

/** Flip for Black at the bottom. Done in render, never in state. */
export const orient = (x: number, y: number, orientation: "white" | "black"): { x: number; y: number } =>
  orientation === "white" ? { x, y } : { x: 7 - x, y: 7 - y };

const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));
const rest = (pieces: PlacedPiece[]): BoardPiece[] =>
  pieces.map((p) => ({ ...p, ...squareXY(p.square), opacity: 1, scale: 1 }));

/**
 * Pure function of the frame: no state carried between frames, so seeking to any frame
 * gives the same result as rendering sequentially. A ply animates from msToFrame(show_at_ms)
 * for pieceMoveMs; if the next ply starts first, the previous one snaps to its end.
 */
export const boardStateAt = (
  frame: number,
  fps: number,
  plies: PlyInput[],
  positions: PlyState[],
): BoardState => {
  let k = -1;
  for (let i = 0; i < plies.length; i++) if (msToFrame(plies[i].show_at_ms, fps) <= frame) k = i;
  if (k < 0) return { ply: 0, pieces: rest(positions[0].pieces), highlights: [], arrows: [] };

  const p = plies[k];
  const prev = positions[p.ply - 1];
  const next = positions[p.ply];
  const move = next.move!;
  const elapsed = frameToMs(frame - msToFrame(p.show_at_ms, fps), fps);
  const landed = elapsed >= motion.pieceMoveMs;
  const popMs = move.promotion ? PROMOTION_POP_MS : 0;

  const arrows = landed ? p.arrows.slice(0, MAX_ARROWS) : [];
  // Last-move tint shows as the move starts; the check marker waits until the move lands.
  const highlights = landed ? p.highlights : p.highlights.filter((h) => h.kind !== "check");

  if (elapsed >= motion.pieceMoveMs + popMs)
    return { ply: p.ply, pieces: rest(next.pieces), highlights, arrows };

  const progress = clamp01(elapsed / motion.pieceMoveMs);
  const eased = motion.enter(progress);
  const slide = (from: string, to: string): { x: number; y: number } => {
    const a = squareXY(from);
    const b = squareXY(to);
    return { x: a.x + (b.x - a.x) * eased, y: a.y + (b.y - a.y) * eased };
  };

  const moverId = prev.pieces.find((q) => q.square === move.from)!.id;
  const still: BoardPiece[] = [];
  const moving: BoardPiece[] = [];
  for (const q of prev.pieces) {
    if (q.id === moverId) {
      const pos = slide(move.from, move.to);
      const after = next.pieces.find((n) => n.id === moverId)!;
      const pop = landed && move.promotion ? (elapsed - motion.pieceMoveMs) / PROMOTION_POP_MS : 0;
      moving.push({
        ...(landed ? after : q),
        ...pos,
        opacity: 1,
        scale: 1 + (PROMOTION_POP_SCALE - 1) * Math.sin(Math.PI * clamp01(pop)),
      });
    } else if (move.castleRook && q.id === move.castleRook.id) {
      moving.push({ ...q, ...slide(move.castleRook.from, move.castleRook.to), opacity: 1, scale: 1 });
    } else if (q.id === move.captured) {
      if (landed) continue;
      const opacity = clamp01((motion.pieceMoveMs - elapsed) / motion.captureFadeMs);
      still.push({ ...q, ...squareXY(q.square), opacity, scale: 1 });
    } else {
      still.push({ ...q, ...squareXY(q.square), opacity: 1, scale: 1 });
    }
  }
  // Moving pieces last so they draw above the rest.
  return { ply: p.ply, pieces: [...still, ...moving], highlights, arrows };
};
