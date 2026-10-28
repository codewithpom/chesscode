import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { boardThemes } from "../theme/boardThemes";
import { useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { Arrows } from "./Arrows";
import { boardStateAt, orient, type BoardState } from "./boardState";
import { Highlights } from "./Highlights";
import { Piece } from "./Piece";
import { buildPositions } from "./positions";
import { Square } from "./Square";

export type BoardThemeName = keyof typeof boardThemes;

// Coordinates sit outside the board, 28 px at the 800 px Studio board (a square is 100 px: 0.28 units).
// The SVG overflows its box on the bottom and right to hold them.
const COORD_SIZE = 0.28;
const COORD_GAP = 0.1;

/** Draws one BoardState (squares, labels, pieces, arrows); shared by Board and LineBoard. */
export const BoardView: FC<{
  state: BoardState;
  size: number;
  orientation: "white" | "black";
  theme: BoardThemeName;
  hideArrows?: boolean;
}> = ({ state, size, orientation, theme, hideArrows }) => {
  useFonts();
  const palette = boardThemes[theme];
  return (
    <svg width={size} height={size} viewBox="0 0 8 8" overflow="visible" style={{ display: "block", overflow: "visible" }}>
      {Array.from({ length: 64 }, (_, i) => {
        const x = i % 8;
        const y = Math.floor(i / 8);
        return <Square key={i} x={x} y={y} fill={(x + y) % 2 === 0 ? palette.light : palette.dark} />;
      })}
      <Highlights highlights={state.highlights} theme={theme} orientation={orientation} />
      {/* Files under the board, ranks to its right; muted on the page background, never over a square. */}
      {Array.from({ length: 8 }, (_, i) => {
        const file = orientation === "white" ? i : 7 - i;
        const rank = orientation === "white" ? 8 - i : i + 1;
        return (
          <g key={i} fill={tokens.color.muted} fontFamily={tokens.font.mono} fontWeight={500} fontSize={COORD_SIZE}>
            <text x={i + 0.5} y={8 + COORD_GAP + COORD_SIZE * 0.78} textAnchor="middle">
              {String.fromCharCode(97 + file)}
            </text>
            <text x={8 + COORD_GAP} y={i + 0.5 + COORD_SIZE * 0.36}>
              {rank}
            </text>
          </g>
        );
      })}
      {state.pieces.map((p) => {
        const o = orient(p.x, p.y, orientation);
        return <Piece key={p.id} type={p.type} color={p.color} x={o.x} y={o.y} opacity={p.opacity} scale={p.scale} />;
      })}
      {!hideArrows && <Arrows arrows={state.arrows} orientation={orientation} />}
    </svg>
  );
};

/**
 * SVG board driven only by the spec and the current frame. `atMs` draws the game at that ms
 * instead of the current frame (cold-open remapping, freeze frames); `hideArrows` drops the move arrows.
 */
export const Board: FC<{ spec: VideoSpec; size: number; atMs?: number; hideArrows?: boolean }> = ({
  spec,
  size,
  atMs,
  hideArrows,
}) => {
  const currentFrame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const frame = atMs === undefined ? currentFrame : msToFrame(atMs, fps);
  const state = boardStateAt(frame, fps, spec.plies, buildPositions(spec.game.pgn));
  return (
    <BoardView state={state} size={size} orientation={spec.board.orientation} theme={spec.board.theme} hideArrows={hideArrows} />
  );
};
