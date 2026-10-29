import type { FC } from "react";
import { LineBoard } from "../board/LineBoard";
import { buildPositions } from "../board/positions";
import type { VideoSpec } from "../spec/schema";
import { useFonts } from "../theme/fonts";
import { studioLayout } from "../theme/layout";
import { LowerLabel } from "../ui/LowerLabel";
import { keyMomentTiming } from "./helpers";
import { MascotSlot } from "./MascotSlot";
import type { SceneRange } from "./timeline";

const { board, label, mascot } = studioLayout.boxes;
/** Slower replay of a beat: the alternative line from the position before the beat's ply, with the label. */
export const KeyMoment: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  useFonts();
  const km = range.keyMoment!;
  const fen = buildPositions(spec.game.pgn)[km.ply - 1].fen;
  const { leadMs, stepMs } = keyMomentTiming(range.endMs - range.startMs, km.line.length);
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
      <MascotSlot spec={spec} box={mascot} height={studioLayout.mascotHeight} />
    </>
  );
};
