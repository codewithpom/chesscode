import type { FC } from "react";
import { motion } from "../theme/motion";
import { tokens } from "../theme/tokens";

const W = 1.1;
const H = 0.72;
const IN_FRAMES = 5;
const OUT_FRAMES = 6;

/** The "!!" stamp on the square's top-right corner: lands from 1.5x to 1x, holds, fades. Kept inside the board. */
export const BrilliantStamp: FC<{ x: number; y: number; t: number; dur: number }> = ({ x, y, t, dur }) => {
  const cx = Math.min(x + 1, 8 - W / 2);
  const cy = Math.max(y, H / 2);
  const land = motion.enter(Math.min(1, t / IN_FRAMES));
  const scale = 1.5 - 0.5 * land;
  const opacity = Math.min(land, Math.min(1, (dur - t) / OUT_FRAMES));
  return (
    <g opacity={opacity} transform={`translate(${cx} ${cy}) scale(${scale})`}>
      <rect x={-W / 2} y={-H / 2} width={W} height={H} fill={tokens.color.bg} stroke={tokens.color.brilliant} strokeWidth={0.05} />
      <text
        x={0}
        y={0.2}
        textAnchor="middle"
        fontFamily={tokens.font.sans}
        fontWeight={600}
        fontSize={0.56}
        fill={tokens.color.brilliant}
      >
        !!
      </text>
    </g>
  );
};
