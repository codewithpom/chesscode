import type { Beat, Ply, VideoSpec } from "../spec/schema";
import { strings } from "./strings";
import { msToFrame } from "../spec/time";
import { motion } from "../theme/motion";
import { studioLayout, type Box } from "../theme/layout";
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

/** `12. Bxb5+` for White's move, `12...Qxf3` for Black's (no space after the dots, as in print). */
export const moveLabel = (p: Pick<Ply, "ply" | "san">): string => `${Math.ceil(p.ply / 2)}${p.ply % 2 === 1 ? ". " : "..."}${p.san}`;

const COLD_LEAD_MS = 800; // the position before the first ply holds this long
const COLD_TAIL_MS = 700;

/**
 * The spec as the ColdOpen shows it: beats of the shown plies move with them, plies before `cold_open.ply_from` are already on the board (no arrows),
 * ply_from..ply_to are spread over the scene range, and the later plies never appear. Board and EvalBar then
 * draw the scene from the ordinary spec data.
 */
export const coldOpenSpec = (spec: VideoSpec, range: Pick<SceneRange, "startMs" | "endMs">): VideoSpec => {
  const { ply_from: from, ply_to: to } = spec.cold_open;
  const n = to - from + 1;
  const step = Math.max(2 * motion.pieceMoveMs, Math.floor((range.endMs - range.startMs - COLD_LEAD_MS - COLD_TAIL_MS) / n));
  const showAt = (ply: number): number => range.startMs + COLD_LEAD_MS + (ply - from) * step;
  return {
    ...spec,
    // The mascot reacts when its beat's ply plays inside the cold open; later beats belong to Playback.
    // Silent (empty line): the same beat speaks when Playback reaches it, and a line is never said twice in one video.
    beats: spec.beats.filter((b) => b.ply >= from && b.ply <= to).map((b) => ({ ...b, at_ms: showAt(b.ply), mascot: { ...b.mascot, line: "" }, sfx: null })),
    plies: spec.plies.map((p) =>
      p.ply < from
        ? { ...p, show_at_ms: -60000, arrows: [] }
        : p.ply <= to
          ? { ...p, show_at_ms: showAt(p.ply) }
          : { ...p, show_at_ms: range.endMs + 60000 },
    ),
  };
};

const KM_LEAD_MS = 1500; // the position holds before the line starts
const KM_HOLD_MS = 1000; // the final position holds before the scene ends
const KM_MAX_STEP_MS = 4500;

/**
 * Pacing of an alternative line inside a KeyMoment of `durationMs`: the first move starts after `leadMs`, a move
 * every `stepMs`, and the last one has landed `KM_HOLD_MS` before the scene ends. The step is whatever the scene
 * allows (up to 4.5 s), so even an 8-move line in 15 s plays to its end.
 */
export const keyMomentTiming = (durationMs: number, moves: number): { leadMs: number; stepMs: number } => {
  if (moves <= 1) return { leadMs: KM_LEAD_MS, stepMs: KM_MAX_STEP_MS };
  const room = durationMs - KM_HOLD_MS - motion.pieceMoveMs - 40; // 40 ms: one frame of rounding
  const leadMs = Math.min(KM_LEAD_MS, Math.max(0, room - (moves - 1) * motion.pieceMoveMs * 2));
  return { leadMs, stepMs: Math.min(KM_MAX_STEP_MS, Math.floor((room - leadMs) / (moves - 1))) };
};

/** Where the long-form captions go at `ms`: the outro moves them to the left third, the right two thirds being the end screen's. undefined = the default right column. */
export const captionsBoxAt = (ranges: Pick<SceneRange, "kind" | "startMs" | "endMs">[], ms: number): Box | undefined =>
  ranges.some((r) => r.kind === "outro" && ms >= r.startMs && ms < r.endMs) ? studioLayout.boxes.outroCaptions : undefined;

const SIGN_OFF_WAVE_AT_MS = 400; // after the cut to the outro
const SIGN_OFF_POINT_AT_MS = 3600; // the wave bubble has run its course (1.8 s + 60 ms a character)

/**
 * The outro sign-off as two beats for the mascot layer: Pyaada waves with a line, then points toward the reserved
 * end-screen area with another. Only these two react in the outro, so a late beat of the game cannot talk over them.
 */
export const signOffBeats = (spec: VideoSpec, range: Pick<SceneRange, "startMs">): Beat[] => {
  const t = strings[spec.language];
  const base = { type: "resign" as const, ply: spec.plies.length, intensity: 1, fx: [], sfx: null };
  return [
    { ...base, beat_id: "outro-wave", at_ms: range.startMs + SIGN_OFF_WAVE_AT_MS, mascot: { pose: "wave", line: t.signOffWave } },
    { ...base, beat_id: "outro-point", at_ms: range.startMs + SIGN_OFF_POINT_AT_MS, mascot: { pose: "point", line: t.signOffPoint } },
  ];
};
