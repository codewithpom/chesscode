import type { FC } from "react";
import { boardThemes } from "../theme/boardThemes";
import type { Highlight } from "./boardState";
import { orient, squareXY } from "./boardState";

type Props = { highlights: Highlight[]; theme: keyof typeof boardThemes; orientation: "white" | "black" };

/** Flat tints under the pieces: soft last-move squares, and the king square on check. No glow filters. */
export const Highlights: FC<Props> = ({ highlights, theme, orientation }) => {
  const palette = boardThemes[theme];
  return (
    <g>
      {highlights.map((h) => {
        const { x, y } = squareXY(h.square);
        const o = orient(x, y, orientation);
        return (
          <rect
            key={h.kind + h.square}
            x={o.x}
            y={o.y}
            width={1}
            height={1}
            fill={h.kind === "check" ? palette.check : palette.lastMove}
            opacity={h.kind === "check" ? 0.75 : 1}
          />
        );
      })}
    </g>
  );
};
