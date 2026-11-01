import type { FC } from "react";
import { tokens } from "../theme/tokens";

/** `m:ss`, seconds floored, minutes not capped. */
export const formatClock = (ms: number): string => {
  const total = Math.floor(Math.max(0, ms) / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
};

/** A player's remaining time. `red` turns it blunder-red (time_scramble); `pulse` (0..1) is a scale pulse (long_think). */
export const Clock: FC<{ ms: number; red?: boolean; pulse?: number }> = ({ ms, red = false, pulse = 0 }) => (
  <span
    style={{
      display: "inline-block",
      fontFamily: tokens.font.mono,
      fontWeight: 500,
      fontSize: tokens.size.body,
      fontVariantNumeric: "tabular-nums",
      color: red ? tokens.color.blunder : tokens.color.text,
      transform: `scale(${1 + 0.08 * pulse})`,
      transformOrigin: "right center",
    }}
  >
    {formatClock(ms)}
  </span>
);
