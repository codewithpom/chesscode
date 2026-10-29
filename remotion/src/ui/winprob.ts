import { spring, type SpringConfig } from "remotion";
import type { Beat, Ply } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { uiSpring } from "../theme/motion";

type Eval = { cp: number | null; mate: number | null };

// Same constant as pipeline/chesscode/winprob.py. Never map raw centipawns linearly.
const K = 0.00368208;

/** White's win percentage, 0..100. Mate for White is 100, mate for Black is 0. */
export const winPct = (e: Eval): number => {
  if (e.mate !== null) return e.mate > 0 ? 100 : e.mate < 0 ? 0 : 50;
  const cp = e.cp ?? 0;
  return 50 + 50 * (2 / (1 + Math.exp(-K * cp)) - 1);
};

const MINUS = "\u2212";

export const evalLabel = (e: Eval): string => {
  if (e.mate !== null) return e.mate < 0 ? `${MINUS}M${-e.mate}` : `M${e.mate}`;
  const v = Math.round((e.cp ?? 0) / 10) / 10;
  if (v === 0) return "0.0";
  return v > 0 ? `+${v.toFixed(1)}` : `${MINUS}${(-v).toFixed(1)}`;
};

const FIGURE_SPACE = " "; // same advance as a digit in Plex Mono

/** evalLabel padded to 5 characters with figure spaces, so a right-aligned label never jumps. */
export const evalLabelFixed = (e: Eval): string => evalLabel(e).padStart(5, FIGURE_SPACE);

/** The same padded on the right, for a left-aligned label (the vertical bar's), so its first character sits on the bar's edge. */
export const evalLabelFixedLeft = (e: Eval): string => evalLabel(e).padEnd(5, FIGURE_SPACE);

/** Same damping ratio as uiSpring at 3x stiffness: faster, still no overshoot. */
export const whipSpring: SpringConfig = {
  ...uiSpring,
  stiffness: uiSpring.stiffness! * 3,
  damping: uiSpring.damping! * Math.sqrt(3),
};

export type BarPly = Pick<Ply, "ply" | "show_at_ms" | "eval" | "class">;
/** `fx` is optional so a bare {type, ply} still means the spec section 5 rule: a blunder whips. */
export type BarBeat = Pick<Beat, "type" | "ply"> & Partial<Pick<Beat, "fx">>;

/** White's share of the bar (0..100) at a frame. Pure: depends only on the frame and spec data. */
export const barShareAt = (frame: number, fps: number, plies: BarPly[], beats: BarBeat[]): number => {
  let k = -1;
  for (let i = 0; i < plies.length; i++) if (msToFrame(plies[i].show_at_ms, fps) <= frame) k = i;
  if (k < 0) return 50;
  const from = k === 0 ? 50 : winPct(plies[k - 1].eval);
  const to = winPct(plies[k].eval);
  // Spec section 5: the bar whips on a blunder beat; any beat can ask for it with the eval_whip effect (comeback).
  const whip = beats.some((b) => b.ply === plies[k].ply && (b.type === "blunder" || b.fx?.includes("eval_whip")));
  const t = spring({
    frame: frame - msToFrame(plies[k].show_at_ms, fps),
    fps,
    config: whip ? whipSpring : uiSpring,
  });
  return Math.min(100, Math.max(0, from + (to - from) * t));
};
