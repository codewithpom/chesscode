import type { FC } from "react";
import type { MoveRow } from "./moveRows";
import { useFonts } from "../theme/fonts";
import { studioLayout, type Box } from "../theme/layout";
import { tokens } from "../theme/tokens";

const ROW = studioLayout.moveRowHeight;
const NO_W = 72;
const CELL_W = 180;

/**
 * The alternative line as Plex Mono rows, the same look as the move list: revealed move by move, the move being
 * played (or about to be, while its arrow is up) highlighted. A row with no White move is a Black-first "12..." row.
 */
export const LineList: FC<{ rows: MoveRow[]; box: Box }> = ({ rows, box }) => {
  useFonts();
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
      {rows.map((r, i) => {
        const cell = (san: string | undefined, side: "w" | "b", x: number) =>
          san === undefined ? null : (
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
                background: r.current === side ? tokens.color.surface : undefined,
                color: r.current === side ? tokens.color.text : tokens.color.muted,
                whiteSpace: "pre",
              }}
            >
              {san}
            </div>
          );
        return (
          <div key={r.no} style={{ position: "absolute", left: 0, top: i * ROW, width: box.w, height: ROW, lineHeight: `${ROW}px` }}>
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
