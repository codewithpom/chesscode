import type { FC } from "react";
import { motion } from "../theme/motion";
import { tokens } from "../theme/tokens";

/** A flat gold bar sweeping once across the square, clipped to it (a glint, not a glow). */
export const GoldGlint: FC<{ id: string; x: number; y: number; t: number; dur: number }> = ({ id, x, y, t, dur }) => {
  const p = motion.enter(Math.min(1, t / dur));
  const left = -0.5 + 2 * p; // bar's left edge, in square units
  return (
    <g>
      <clipPath id={`glint-${id}`}>
        <rect x={x} y={y} width={1} height={1} />
      </clipPath>
      <g clipPath={`url(#glint-${id})`} opacity={p > 0.9 ? (1 - p) * 10 : 1}>
        <polygon
          points={`${x + left},${y + 1} ${x + left + 0.18},${y + 1} ${x + left + 0.18 + 0.3},${y} ${x + left + 0.3},${y}`}
          fill={tokens.color.brilliant}
          opacity={0.75}
        />
      </g>
    </g>
  );
};
