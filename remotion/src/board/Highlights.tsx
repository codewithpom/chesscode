import type { FC } from "react";
import { boardThemes } from "../theme/boardThemes";
import type { Highlight } from "./boardState";
import { orient, squareXY } from "./boardState";

type Props = { highlights: Highlight[]; theme: keyof typeof boardThemes; orientation: "white" | "black" };

const CHECK_STROKE = 0.06;

/**
 * Flat marks under the pieces. Last move: the square swaps to an opaque tint of its own color.
 * Check: the square keeps its fill and gets an inset stroke. No wash, no glow filters.
 */
export const Highlights: FC<Props> = ({ highlights, theme, orientation }) => {
  const palette = boardThemes[theme];
  return (
    <g>
      {highlights.map((h) => {
        const { x, y } = squareXY(h.square);
        const o = orient(x, y, orientation);
        if (h.kind === "check")
          return (
            <rect
              key={h.kind + h.square}
              x={o.x + CHECK_STROKE / 2}
              y={o.y + CHECK_STROKE / 2}
              width={1 - CHECK_STROKE}
              height={1 - CHECK_STROKE}
              fill="none"
              stroke={palette.check}
              strokeWidth={CHECK_STROKE}
            />
          );
        // Square color parity is unchanged by the 180 degree flip.
        const light = (x + y) % 2 === 0;
        return (
          <rect
            key={h.kind + h.square}
            x={o.x}
            y={o.y}
            width={1}
            height={1}
            fill={light ? palette.lastMoveLight : palette.lastMoveDark}
          />
        );
      })}
    </g>
  );
};
