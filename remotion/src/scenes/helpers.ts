import type { Ply, VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { motion } from "../theme/motion";
import type { SceneRange } from "./timeline";

/** The ply on screen at an absolute frame (the last whose show_at_ms has been reached), or null before the first. */
export const currentPlyAt = (plies: Pick<Ply, "ply" | "show_at_ms">[], frame: number, fps: number): number | null => {
  let k: number | null = null;
  for (let i = 0; i < plies.length; i++) if (msToFrame(plies[i].show_at_ms, fps) <= frame) k = plies[i].ply;
  return k;
};

/** Remaining clock of one side after the latest of its plies up to `ply`, or null when the spec has no clock data for it. */
export const clockFor = (plies: Pick<Ply, "ply" | "clock_ms">[], side: "white" | "black", ply: number): number | null => {
  const parity = side === "white" ? 1 : 0;
  for (let i = Math.min(ply, plies.length) - 1; i >= 0; i--) {
    if (plies[i].ply % 2 === parity && plies[i].clock_ms !== null) return plies[i].clock_ms;
  }
  return null;
};

/** Four-digit year of `game.date` ("1858-11-02", "1858.??.??"), or "". */
export const yearOf = (date: string): string => /\d{4}/.exec(date)?.[0] ?? "";

const RESULT: Record<VideoSpec["game"]["result"], string> = { "1-0": "1–0", "0-1": "0–1", "1/2-1/2": "½–½" };
export const resultText = (r: VideoSpec["game"]["result"]): string => RESULT[r];

/** `12. Bxb5+` for White's move, `12... Qxf3` for Black's. */
export const moveLabel = (p: Pick<Ply, "ply" | "san">): string => `${Math.ceil(p.ply / 2)}${p.ply % 2 === 1 ? "." : "..."} ${p.san}`;

const COLD_LEAD_MS = 800; // the position before the first ply holds this long
const COLD_TAIL_MS = 700;

/**
 * The spec as the ColdOpen shows it: plies before `cold_open.ply_from` are already on the board (no arrows),
 * ply_from..ply_to are spread over the scene range, and the later plies never appear. Board and EvalBar then
 * draw the scene from the ordinary spec data.
 */
export const coldOpenSpec = (spec: VideoSpec, range: Pick<SceneRange, "startMs" | "endMs">): VideoSpec => {
  const { ply_from: from, ply_to: to } = spec.cold_open;
  const n = to - from + 1;
  const step = Math.max(2 * motion.pieceMoveMs, Math.floor((range.endMs - range.startMs - COLD_LEAD_MS - COLD_TAIL_MS) / n));
  return {
    ...spec,
    plies: spec.plies.map((p) =>
      p.ply < from
        ? { ...p, show_at_ms: -60000, arrows: [] }
        : p.ply <= to
          ? { ...p, show_at_ms: range.startMs + COLD_LEAD_MS + (p.ply - from) * step }
          : { ...p, show_at_ms: range.endMs + 60000 },
    ),
  };
};
