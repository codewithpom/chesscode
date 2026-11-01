import type { FC } from "react";
import { Arrows } from "../board/Arrows";
import { motion } from "../theme/motion";

const IN_FRAMES = 8;
const OUT_FRAMES = 10;

/** The move that was missed, as the existing dashed `missed` arrow, fading in and out. */
export const GhostArrow: FC<{ uci: string; orientation: "white" | "black"; t: number; dur: number }> = ({ uci, orientation, t, dur }) => (
  <g opacity={motion.enter(Math.min(1, t / IN_FRAMES)) * Math.min(1, (dur - t) / OUT_FRAMES)}>
    <Arrows arrows={[{ from: uci.slice(0, 2), to: uci.slice(2, 4), color: "missed" }]} orientation={orientation} />
  </g>
);
