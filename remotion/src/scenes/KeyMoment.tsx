import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { frameToMs } from "../spec/time";
import { LineBoard } from "../board/LineBoard";
import { buildPositions } from "../board/positions";
import type { VideoSpec } from "../spec/schema";
import { useFonts } from "../theme/fonts";
import { studioLayout } from "../theme/layout";
import { LowerLabel } from "../ui/LowerLabel";
import { LineList } from "../ui/LineList";
import { activeLineMove, keyMomentTiming, lineMoves, lineRows } from "./helpers";
import { MascotSlot } from "./MascotSlot";
import type { SceneRange } from "./timeline";

const { board, label, mascot, moveList } = studioLayout.boxes;
/** Slower replay of a beat: the alternative line from the position before the beat's ply, with the label. */
export const KeyMoment: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  useFonts();
  const km = range.keyMoment!;
  const fen = buildPositions(spec.game.pgn)[km.ply - 1].fen;
  const { leadMs, stepMs } = keyMomentTiming(range.endMs - range.startMs, km.line.length);
  const { fps } = useVideoConfig();
  const moves = lineMoves(fen, km.line);
  const active = activeLineMove(frameToMs(useCurrentFrame(), fps) - (range.startMs + leadMs), stepMs, moves.length);
  return (
    <>
      <div style={{ position: "absolute", left: board.x, top: board.y }}>
        <LineBoard
          fen={fen}
          line={km.line}
          startMs={range.startMs + leadMs}
          stepMs={stepMs}
          size={board.w}
          orientation={spec.board.orientation}
          theme={spec.board.theme}
        />
      </div>
      <div style={{ position: "absolute", left: label.x, top: label.y, width: label.w, height: label.h }}>
        <LowerLabel text={km.label} startMs={range.startMs} endMs={range.endMs} lang={spec.language} />
      </div>
      <LineList rows={lineRows(moves, active)} box={moveList} />
      <MascotSlot spec={spec} box={mascot} height={studioLayout.mascotHeight} />
    </>
  );
};
