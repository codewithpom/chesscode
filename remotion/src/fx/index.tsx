import type { FC } from "react";
import { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { orient, squareXY } from "../board/boardState";
import { buildPositions } from "../board/positions";
import type { VideoSpec } from "../spec/schema";
import { GoldGlint } from "./glint";
import { GhostArrow } from "./ghostArrow";
import { RedFlash } from "./flash";
import { CrownSparkle } from "./sparkle";
import { BrilliantStamp } from "./stamp";
import { kingPath, KingTrail } from "./trail";
import { fxWindows } from "./windows";

export { OutOfTheoryLabel, OUT_OF_THEORY } from "./label";
export { ShakeBox, shakeOffset } from "./shake";
export { activeWindow, boardMsAt, fxWindows, type FxWindow } from "./windows";

/** Top-left of a square in oriented board units. */
const at = (sq: string, o: "white" | "black") => {
  const { x, y } = squareXY(sq);
  return orient(x, y, o);
};

/**
 * Overlay drawn above the board (same box as the board, absolute frame): red flash, gold glint, "!!" stamp,
 * ghost arrow, king trail, crown sparkle. Shake, replay and freeze act on the board itself (ShakeBox, boardMsAt).
 */
export const BoardFx: FC<{ spec: VideoSpec; size: number; orientation: "white" | "black"; template: "studio" | "shorts" }> = ({
  spec,
  size,
  orientation,
  template,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const windows = useMemo(() => fxWindows(spec.beats, fps, { template, plies: spec.plies }), [spec.beats, spec.plies, fps, template]);
  const states = buildPositions(spec.game.pgn);

  const parts = windows
    .filter((w) => frame >= w.from && frame < w.to)
    .map((w) => {
      const t = frame - w.from;
      const dur = w.to - w.from;
      const move = states[w.beat.ply]?.move;
      if (!move) return null;
      const { x, y } = at(move.to, orientation);
      const key = `${w.beat.beat_id}-${w.fx}`;
      switch (w.fx) {
        case "red_flash": return <RedFlash key={key} x={x} y={y} t={t} dur={dur} />;
        case "gold_glint": return <GoldGlint key={key} id={key} x={x} y={y} t={t} dur={dur} />;
        case "stamp_brilliant": return <BrilliantStamp key={key} x={x} y={y} t={t} dur={dur} />;
        case "crown_sparkle": return <CrownSparkle key={key} x={x} y={y} t={t} dur={dur} />;
        case "ghost_arrow":
          return <GhostArrow key={key} uci={spec.plies[w.beat.ply - 1].best_uci} orientation={orientation} t={t} dur={dur} />;
        case "king_trail": {
          const color = w.beat.ply % 2 === 1 ? "w" : "b";
          const points = kingPath(states, w.beat.ply, color).map((sq) => {
            const p = at(sq, orientation);
            return { x: p.x + 0.5, y: p.y + 0.5 };
          });
          return <KingTrail key={key} points={points} t={t} dur={dur} />;
        }
        default: return null;
      }
    });

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 8 8"
      style={{ position: "absolute", left: 0, top: 0, overflow: "visible", pointerEvents: "none" }}
    >
      {parts}
    </svg>
  );
};
