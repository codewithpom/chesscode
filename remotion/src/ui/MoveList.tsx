import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { VideoSpec } from "../spec/schema";
import { frameToMs, msToFrame } from "../spec/time";
import { useFonts } from "../theme/fonts";
import { studioLayout, type Box } from "../theme/layout";
import { motion } from "../theme/motion";
import { tokens } from "../theme/tokens";
import { allRows, totalRows, windowStart } from "./moveRows";

export { moveRows } from "./moveRows";

const ROW = studioLayout.moveRowHeight;
const NO_W = 72;
const CELL_W = 180;
// Class colour plus a text mark, so colour is never the only signal (brilliant and mistake are both amber).
export const CLASS_STYLE: Partial<Record<VideoSpec["plies"][number]["class"], { color: string; mark: string }>> = {
  best: { color: tokens.color.best, mark: "" },
  brilliant: { color: tokens.color.brilliant, mark: "!!" },
  mistake: { color: tokens.color.mistake, mark: "?" },
  blunder: { color: tokens.color.blunder, mark: "??" },
};
const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

/**
 * Nine rows, the current move's row centred (clamped at both ends of the game). Reads the absolute frame.
 * The window scrolls one row over uiEnterMs when the move changes.
 */
export const MoveList: FC<{ spec: VideoSpec; box: Box; underline?: boolean }> = ({ spec, box, underline: underlineOn = true }) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  let k = -1;
  for (let i = 0; i < spec.plies.length; i++) if (msToFrame(spec.plies[i].show_at_ms, fps) <= frame) k = i;
  const current = k < 0 ? null : spec.plies[k];
  const rows = allRows(spec.plies, current?.ply ?? 0);
  const rowOf = (ply: number): number => Math.max(1, Math.ceil(ply / 2));
  const total = totalRows(spec.plies);
  const to = windowStart(total, rowOf(current?.ply ?? 0));
  const from = windowStart(total, rowOf(k > 0 ? spec.plies[k - 1].ply : 0));
  const elapsed = k < 0 ? Infinity : frameToMs(frame - msToFrame(current!.show_at_ms, fps), fps);
  const scroll = from + (to - from) * motion.enter(clamp01(elapsed / motion.uiEnterMs));
  const marked = current ? CLASS_STYLE[current.class] : undefined;
  const underline =
    underlineOn && !!current && spec.beats.some((b) => b.type === "mistake" && b.ply === current.ply && b.fx.includes("move_underline"));

  return (
    <div
      style={{
        position: "absolute",
        left: box.x,
        top: box.y,
        width: box.w,
        height: box.h,
        overflow: "hidden",
        fontFamily: tokens.font.mono,
        fontWeight: 500,
        fontSize: tokens.size.body,
        fontVariantNumeric: "tabular-nums",
        color: tokens.color.muted,
      }}
    >
      {rows.map((r) => {
        const y = (r.no - scroll) * ROW;
        if (y < -ROW || y > box.h) return null;
        const cell = (san: string | undefined, side: "w" | "b", x: number) => {
          if (san === undefined) return null;
          const isCurrent = r.current === side;
          return (
            <div
              key={side}
              style={{
                position: "absolute",
                left: x,
                top: 0,
                width: CELL_W,
                height: ROW,
                lineHeight: `${ROW}px`,
                paddingLeft: tokens.space(1),
                boxSizing: "border-box",
                background: isCurrent ? tokens.color.surface : undefined,
                color: isCurrent ? (marked?.color ?? tokens.color.text) : tokens.color.muted,
                whiteSpace: "pre",
              }}
            >
              <span style={{ borderBottom: isCurrent && underline ? `3px solid ${tokens.color.mistake}` : "3px solid transparent" }}>
                {san}
                {isCurrent ? marked?.mark : ""}
              </span>
            </div>
          );
        };
        return (
          <div key={r.no} style={{ position: "absolute", left: 0, top: y, width: box.w, height: ROW, lineHeight: `${ROW}px` }}>
            <span style={{ position: "absolute", left: 0, width: NO_W, textAlign: "right", paddingRight: tokens.space(1), boxSizing: "border-box" }}>
              {r.no}.{r.white === undefined ? ".." : ""}
            </span>
            {cell(r.white, "w", NO_W)}
            {cell(r.black, "b", NO_W + CELL_W)}
          </div>
        );
      })}
    </div>
  );
};
