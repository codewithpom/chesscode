import type { Beat, Ply } from "../spec/schema";
import { frameToMs, msToFrame } from "../spec/time";
import { motion } from "../theme/motion";
import { templateFx, type FxId } from "../theme/templates";

export type FxWindow = { fx: FxId; beat: Beat; from: number; to: number };

// Frame counts of the beat table (docs/SPEC.md section 8, plan task 4).
const SHAKE = 6;
const FLASH = 8;
const FREEZE = 6; // the plan's own 6-frame rule; M4's freezeAt replaces it once merged
const GLINT = 24;
const GHOST = 60;
const TRAIL = 90;
const SPARKLE = 30;
const LABEL = 60;
const CLOCK_FALLBACK = 90; // last ply of the video has no "next ply" to end on

type Opts = { template?: "studio" | "shorts"; plies?: Pick<Ply, "ply" | "show_at_ms">[] };

/**
 * One window (frames, `to` exclusive) per enabled effect of every beat. Motion effects start when the move
 * lands (at_ms + 280 ms); board_shake and the out-of-theory label start at at_ms; replay_move re-runs the
 * move right after the 6-frame freeze; clock effects last until the next ply. eval_whip (EvalBar) and
 * move_underline (MoveList) draw themselves and have no window.
 */
export const fxWindows = (beats: Beat[], fps: number, opts: Opts = {}): FxWindow[] => {
  const on = templateFx[opts.template ?? "studio"];
  const move = msToFrame(motion.pieceMoveMs, fps);
  const out: FxWindow[] = [];
  for (const beat of beats) {
    const at = msToFrame(beat.at_ms, fps);
    const land = at + move;
    const nextPly = opts.plies?.find((p) => p.ply === beat.ply + 1);
    const ply = (fx: FxId): [number, number] | null => {
      switch (fx) {
        case "board_shake": return [at, at + SHAKE];
        case "red_flash": return [land, land + FLASH];
        case "freeze_frame": return [land, land + FREEZE];
        case "replay_move": return [land + FREEZE, land + FREEZE + move];
        case "gold_glint":
        case "stamp_brilliant": return [land, land + GLINT];
        case "ghost_arrow": return [land, land + GHOST];
        case "king_trail": return [land, land + TRAIL];
        case "crown_sparkle": return [land, land + SPARKLE];
        case "out_of_theory_label": return [at, at + LABEL];
        case "clock_pulse":
        case "clock_red": return [at, nextPly ? msToFrame(nextPly.show_at_ms, fps) : at + CLOCK_FALLBACK];
        default: return null;
      }
    };
    for (const fx of beat.fx) {
      const w = on[fx] ? ply(fx) : null;
      if (w) out.push({ fx, beat, from: w[0], to: w[1] });
    }
  }
  return out;
};

export const activeWindow = (windows: FxWindow[], fx: FxId, frame: number): FxWindow | undefined =>
  windows.find((w) => w.fx === fx && frame >= w.from && frame < w.to);

/**
 * The ms the board should draw at: held while freeze_frame is on, and during replay_move the ply's 280 ms
 * move runs again from its start. Outside those windows it is the real time, so nothing jumps.
 */
export const boardMsAt = (frame: number, fps: number, windows: FxWindow[], nowMs: number): number => {
  const replay = windows.find((w) => w.fx === "replay_move" && frame >= w.from && frame < w.to);
  if (replay) return replay.beat.at_ms + frameToMs(frame - replay.from, fps);
  const freeze = windows.find((w) => w.fx === "freeze_frame" && frame >= w.from && frame < w.to);
  if (freeze) return frameToMs(freeze.from, fps);
  return nowMs;
};
