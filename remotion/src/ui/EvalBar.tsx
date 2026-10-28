import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { barShareAt, evalLabelFixed } from "./winprob";

type Props = {
  spec: VideoSpec;
  orientation: "vertical" | "horizontal";
  /** Long axis in px. */
  length: number;
  /** Short axis in px. */
  thickness: number;
};

/**
 * White's share fills from the board's bottom (vertical) or left (horizontal) edge; when the board
 * is shown with Black at the bottom the fill starts from the opposite end, matching the board.
 * The numeric label sits just outside the bar (above it), so the caller must leave that room.
 */
export const EvalBar: FC<Props> = ({ spec, orientation, length, thickness }) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const share = barShareAt(frame, fps, spec.plies, spec.beats);

  let current = -1;
  for (let i = 0; i < spec.plies.length; i++)
    if (msToFrame(spec.plies[i].show_at_ms, fps) <= frame) current = i;
  const e = current < 0 ? { cp: 0, mate: null } : spec.plies[current].eval;

  const vertical = orientation === "vertical";
  const flipped = spec.board.orientation === "black";
  const fillPx = (length * share) / 100;
  const fillStyle = vertical
    ? { left: 0, width: thickness, height: fillPx, [flipped ? "top" : "bottom"]: 0 }
    : { top: 0, height: thickness, width: fillPx, [flipped ? "right" : "left"]: 0 };

  return (
    <div
      style={{
        position: "relative",
        width: vertical ? thickness : length,
        height: vertical ? length : thickness,
        background: tokens.color.evalBlack,
        outline: `1px solid ${tokens.color.hairline}`,
              }}
    >
      <div style={{ position: "absolute", background: tokens.color.text, ...fillStyle }} />
      <div
        style={{
          position: "absolute",
          bottom: "100%",
          marginBottom: tokens.space(1),
          [vertical ? "left" : "right"]: 0,
          whiteSpace: "pre",
          color: tokens.color.text,
          fontFamily: tokens.font.mono,
          fontWeight: 500,
          fontSize: tokens.size.evalLabel,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1,
        }}
      >
        {evalLabelFixed(e)}
      </div>
    </div>
  );
};
