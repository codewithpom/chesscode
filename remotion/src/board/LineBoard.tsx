import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { frameToMs } from "../spec/time";
import { motion } from "../theme/motion";
import { BoardView, type BoardThemeName } from "./Board";
import { boardStateAt, type PlyInput } from "./boardState";
import { lineStates } from "./positions";

export { lineStates };

/** Which move of the line is next once the current one has landed, or null while a move is sliding / the line is done. */
export const nextArrowIndex = (elapsedMs: number, stepMs: number, length: number): number | null => {
  const k = elapsedMs < 0 ? -1 : Math.floor(elapsedMs / stepMs);
  const sinceStart = k < 0 ? Infinity : elapsedMs - k * stepMs;
  if (k >= 0 && sinceStart < motion.pieceMoveMs) return null;
  return k + 1 < length ? k + 1 : null;
};

/**
 * Plays an alternative line from `fen`: one move every `stepMs` from `startMs` (scene-local ms of the
 * current frame), 280 ms piece motion, and an arrow for the move about to be played.
 */
export const LineBoard: FC<{
  fen: string;
  line: string[];
  startMs: number;
  stepMs: number;
  size: number;
  orientation: "white" | "black";
  theme: BoardThemeName;
}> = ({ fen, line, startMs, stepMs, size, orientation, theme }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const positions = lineStates(fen, line);
  const plies: PlyInput[] = line.map((_, i) => {
    const mv = positions[i + 1].move!;
    return {
      ply: i + 1,
      show_at_ms: startMs + i * stepMs,
      arrows: [],
      highlights: [
        { square: mv.from, kind: "last_move" },
        { square: mv.to, kind: "last_move" },
      ],
    };
  });
  const next = nextArrowIndex(frameToMs(frame, fps) - startMs, stepMs, line.length);
  const shown = boardStateAt(frame, fps, plies, positions);
  const arrow = next === null ? [] : [{ from: line[next].slice(0, 2), to: line[next].slice(2, 4), color: "best" as const }];
  return <BoardView state={{ ...shown, arrows: arrow }} size={size} orientation={orientation} theme={theme} />;
};
