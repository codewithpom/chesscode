import type { FC } from "react";
import { tokens } from "../theme/tokens";
import type { Arrow } from "./boardState";
import { orient, squareXY } from "./boardState";

const COLOR = { best: tokens.color.best, threat: tokens.color.blunder, missed: tokens.color.mistake } as const;
const WIDTH = 0.16;
const HEAD = 0.42;

type Props = { arrows: Arrow[]; orientation: "white" | "black" };

/** Max 2 arrows (caller slices). `missed` is dashed so it is not told apart by color alone. */
export const Arrows: FC<Props> = ({ arrows, orientation }) => (
  <g opacity={0.9}>
    {arrows.slice(0, 2).map((a) => {
      const f = squareXY(a.from);
      const t = squareXY(a.to);
      const of = orient(f.x, f.y, orientation);
      const ot = orient(t.x, t.y, orientation);
      const x1 = of.x + 0.5;
      const y1 = of.y + 0.5;
      const x2 = ot.x + 0.5;
      const y2 = ot.y + 0.5;
      const len = Math.hypot(x2 - x1, y2 - y1);
      const ux = (x2 - x1) / len;
      const uy = (y2 - y1) / len;
      const bx = x2 - ux * HEAD;
      const by = y2 - uy * HEAD;
      const nx = -uy * (HEAD * 0.55);
      const ny = ux * (HEAD * 0.55);
      const c = COLOR[a.color];
      return (
        <g key={a.from + a.to + a.color}>
          <line
            x1={x1}
            y1={y1}
            x2={bx}
            y2={by}
            stroke={c}
            strokeWidth={WIDTH}
            strokeLinecap="butt"
            strokeDasharray={a.color === "missed" ? "0.22 0.14" : undefined}
          />
          <polygon points={`${x2},${y2} ${bx + nx},${by + ny} ${bx - nx},${by - ny}`} fill={c} />
        </g>
      );
    })}
  </g>
);
