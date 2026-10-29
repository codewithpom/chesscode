import type { FC } from "react";
import { Board } from "../board/Board";
import { BoardFx, ShakeBox } from "../fx";
import { templateFx } from "../theme/templates";
import { studioLayout } from "../theme/layout";
import type { VideoSpec } from "../spec/schema";
import { EvalBar } from "../ui/EvalBar";

const { board, evalBar } = studioLayout.boxes;

/** EvalBar reads the beats for its whip (blunders and beats listing eval_whip); with eval_whip switched off for the template it sees none. */
export const evalSpec = (spec: VideoSpec, template: "studio" | "shorts"): VideoSpec =>
  templateFx[template].eval_whip ? spec : { ...spec, beats: [] };

/**
 * The board at its fixed Studio place with the eval bar beside it. Reads the absolute frame. `atMs` pins the
 * board to a time (freeze, replay, cold open); `fx` adds shake and the board overlay for the spec's beats.
 */
export const StudioBoard: FC<{
  spec: VideoSpec;
  atMs?: number;
  ply?: number;
  hideArrows?: boolean;
  fx?: boolean;
  showEval?: boolean;
}> = ({ spec, atMs, ply, hideArrows, fx = false, showEval = true }) => {
  const inner = (
    <div style={{ position: "relative", width: board.w, height: board.h }}>
      <Board spec={spec} size={board.w} atMs={atMs} ply={ply} hideArrows={hideArrows} />
      {fx && <BoardFx spec={spec} size={board.w} orientation={spec.board.orientation} template="studio" />}
    </div>
  );
  return (
    <>
      {showEval && (
        <div style={{ position: "absolute", left: evalBar.x, top: evalBar.y }}>
          <EvalBar spec={evalSpec(spec, "studio")} orientation="vertical" length={evalBar.h} thickness={evalBar.w} />
        </div>
      )}
      <div style={{ position: "absolute", left: board.x, top: board.y, width: board.w, height: board.h }}>
        {fx ? (
          <ShakeBox beats={spec.beats} template="studio">
            {inner}
          </ShakeBox>
        ) : (
          inner
        )}
      </div>
    </>
  );
};
