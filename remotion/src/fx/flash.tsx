import type { FC } from "react";
import { motion } from "../theme/motion";
import { tokens } from "../theme/tokens";

/** Flat blunder-red wash on the moved piece's square, easing out over the window. No blur, no glow. */
export const RedFlash: FC<{ x: number; y: number; t: number; dur: number }> = ({ x, y, t, dur }) => (
  <rect x={x} y={y} width={1} height={1} fill={tokens.color.blunder} opacity={0.6 * (1 - motion.exit(t / dur))} />
);
