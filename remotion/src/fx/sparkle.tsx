import type { FC } from "react";
import { motion } from "../theme/motion";
import { tokens } from "../theme/tokens";

// Four-point stars at fixed offsets from the square centre (board units); sizes differ so it is not a ring of copies.
const STARS = [
  { dx: -0.42, dy: -0.42, r: 0.2 },
  { dx: 0.44, dy: -0.3, r: 0.14 },
  { dx: 0.36, dy: 0.44, r: 0.18 },
  { dx: -0.4, dy: 0.34, r: 0.12 },
] as const;
const STAGGER = 3;

const star = (r: number): string => {
  const k = r * 0.28;
  return `0,${-r} ${k},${-k} ${r},0 ${k},${k} 0,${r} ${-k},${k} ${-r},0 ${-k},${-k}`;
};

/** Flat gold stars popping around the promotion square, staggered by 3 frames, each swelling then shrinking. */
export const CrownSparkle: FC<{ x: number; y: number; t: number; dur: number }> = ({ x, y, t, dur }) => (
  <g>
    {STARS.map((s, i) => {
      const life = Math.min(1, Math.max(0, (t - i * STAGGER) / (dur - STARS.length * STAGGER)));
      const size = Math.sin(Math.PI * motion.enter(life));
      return (
        <polygon key={i} points={star(s.r)} fill={tokens.color.brilliant} transform={`translate(${x + 0.5 + s.dx} ${y + 0.5 + s.dy}) scale(${size})`} />
      );
    })}
  </g>
);
