import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { VideoSpec } from "../spec/schema";
import { boardThemes } from "../theme/boardThemes";
import { useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { Arrows } from "./Arrows";
import { boardStateAt, orient } from "./boardState";
import { Highlights } from "./Highlights";
import { Piece } from "./Piece";
import { buildPositions } from "./positions";
import { Square } from "./Square";

// Coordinates are 28 px at the 800 px Studio board (a square is 100 px, so 0.28 board units).
const COORD_SIZE = 0.28;

/** SVG board driven only by the spec and the current frame. */
export const Board: FC<{ spec: VideoSpec; size: number }> = ({ spec, size }) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { orientation, theme } = spec.board;
  const palette = boardThemes[theme];
  const state = boardStateAt(frame, fps, spec.plies, buildPositions(spec.game.pgn));

  return (
    <svg width={size} height={size} viewBox="0 0 8 8" style={{ display: "block" }}>
      {Array.from({ length: 64 }, (_, i) => {
        const x = i % 8;
        const y = Math.floor(i / 8);
        return <Square key={i} x={x} y={y} fill={(x + y) % 2 === 0 ? palette.light : palette.dark} />;
      })}
      <Highlights highlights={state.highlights} theme={theme} orientation={orientation} />
      {/* File letters along the bottom row, rank numbers down the left column, drawn under the pieces. */}
      {Array.from({ length: 8 }, (_, i) => {
        const file = orientation === "white" ? i : 7 - i;
        const rank = orientation === "white" ? 8 - i : i + 1;
        return (
          <g key={i} fill={palette.coord} fontFamily={tokens.font.mono} fontWeight={500} fontSize={COORD_SIZE}>
            <text x={0.06} y={i + 0.06 + COORD_SIZE * 0.8}>
              {rank}
            </text>
            <text x={i + 0.94} y={7.94} textAnchor="end">
              {String.fromCharCode(97 + file)}
            </text>
          </g>
        );
      })}
      {state.pieces.map((p) => {
        const o = orient(p.x, p.y, orientation);
        return <Piece key={p.id} type={p.type} color={p.color} x={o.x} y={o.y} opacity={p.opacity} scale={p.scale} />;
      })}
      <Arrows arrows={state.arrows} orientation={orientation} />
    </svg>
  );
};
