import type { FC } from "react";
import { pieceBlack } from "../theme/boardThemes";
import { tokens } from "../theme/tokens";

const DRAW_FRAMES = 24;
const FADE_FRAMES = 18;
const MAX_STEPS = 4;

/** Squares the king of `color` has visited, oldest first (start square, then each destination), last `MAX_STEPS` moves. */
export const kingPath = (
  states: { move: { from: string; to: string } | null; pieces: { square: string; type: string; color: string }[] }[],
  upToPly: number,
  color: "w" | "b",
): string[] => {
  const steps: { from: string; to: string }[] = [];
  for (let i = 1; i <= Math.min(upToPly, states.length - 1); i++) {
    const m = states[i].move!;
    const mover = states[i - 1].pieces.find((p) => p.square === m.from)!;
    if (mover.type === "k" && mover.color === color) steps.push(m);
  }
  const last = steps.slice(-MAX_STEPS);
  return last.length ? [last[0].from, ...last.map((s) => s.to)] : [];
};

/** The king's recent path as a light-cased dark line drawn on over 24 frames and faded over the last 18. `points` are square centres in board units. */
export const KingTrail: FC<{ points: { x: number; y: number }[]; t: number; dur: number }> = ({ points, t, dur }) => {
  if (points.length < 2) return null;
  const d = points.map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join(" ");
  const draw = Math.min(1, t / DRAW_FRAMES);
  const opacity = Math.min(1, (dur - t) / FADE_FRAMES);
  const common = { d, fill: "none", pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - draw, strokeLinejoin: "round" as const };
  return (
    <g opacity={opacity}>
      <path {...common} stroke={tokens.color.text} strokeWidth={0.2} />
      <path {...common} stroke={pieceBlack} strokeWidth={0.1} />
    </g>
  );
};
