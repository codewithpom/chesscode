import type { FC } from "react";
import { tokens } from "../theme/tokens";
import type { Arrow } from "./boardState";
import { orient, squareXY } from "./boardState";

const COLOR = { best: tokens.color.best, threat: tokens.color.threat, missed: tokens.color.mistake } as const;
const WIDTH = 0.16;
const HEAD = 0.42;

type Props = {
  arrows: Arrow[];
  orientation: "white" | "black";
  /** Shaft width in board units (default 0.16). */
  width?: number;
  /** How far the tip stops short of the target square's centre, in board units (default 0: it points at the centre). */
  tipInset?: number;
};

/** Where an arrow's line is drawn, in oriented board units: shaft from (x1,y1) to (bx,by), head tip (x2,y2) and its base corners. */
export const arrowGeometry = (a: Arrow, orientation: "white" | "black", tipInset = 0) => {
  const f = squareXY(a.from);
  const t = squareXY(a.to);
  const of = orient(f.x, f.y, orientation);
  const ot = orient(t.x, t.y, orientation);
  const x1 = of.x + 0.5;
  const y1 = of.y + 0.5;
  const cx = ot.x + 0.5;
  const cy = ot.y + 0.5;
  const len = Math.hypot(cx - x1, cy - y1);
  const ux = (cx - x1) / len;
  const uy = (cy - y1) / len;
  const x2 = cx - ux * tipInset;
  const y2 = cy - uy * tipInset;
  const bx = x2 - ux * HEAD;
  const by = y2 - uy * HEAD;
  const nx = -uy * (HEAD * 0.55);
  const ny = ux * (HEAD * 0.55);
  return { x1, y1, x2, y2, bx, by, nx, ny };
};

/** Max 2 arrows (caller slices). `missed` is dashed so it is not told apart by color alone. */
export const Arrows: FC<Props> = ({ arrows, orientation, width = WIDTH, tipInset = 0 }) => (
  <g opacity={0.9}>
    {arrows.slice(0, 2).map((a) => {
      const { x1, y1, x2, y2, bx, by, nx, ny } = arrowGeometry(a, orientation, tipInset);
      const c = COLOR[a.color];
      return (
        <g key={a.from + a.to + a.color}>
          <line
            x1={x1}
            y1={y1}
            x2={bx}
            y2={by}
            stroke={c}
            strokeWidth={width}
            strokeLinecap="butt"
            strokeDasharray={a.color === "missed" ? "0.22 0.14" : undefined}
          />
          <polygon points={`${x2},${y2} ${bx + nx},${by + ny} ${bx - nx},${by - ny}`} fill={c} />
        </g>
      );
    })}
  </g>
);
