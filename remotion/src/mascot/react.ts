import { spring } from "remotion";
import type { Beat } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { idleAt } from "./idle";
import { POSES } from "./poses";
import { lerpPose, type PoseState } from "./poseState";

// Comic timing (docs/SPEC.md section 8): freeze 6 frames, react on frame 7, bubble text from frame 10.
// Mascot-only spring: critically damped (damping = 2 * sqrt(stiffness)), snappier than the shared UI spring so the
// frame-7 reaction lands as a snap instead of a 0.5 s settle.
const MASCOT_SPRING = { damping: 40, mass: 1, stiffness: 400 };
const NO_BLINK_FRAMES = 30; // eyes do the acting: no blink right after a reaction starts
const FREEZE_FRAMES = 6;
const BUBBLE_DELAY = 3; // frames from the reaction to the bubble (frame 7 -> frame 10)
// Faint: 4 frames of anticipation (tips back), an ease-in fall out of frame, back in 1.5 s later over 12 frames.
const FAINT_ANTICIPATE = 4;
const FAINT_ANTICIPATE_LEAN = -25;
const FAINT_FALL = 12;
const FAINT_BACK_FRAMES = 12;
const FAINT_BACK_MS = 1500;
const FAINT_X = POSES.faint.offsetX;
const FAINT_Y = POSES.faint.offsetY;
const FAINT_LEAN = POSES.faint.lean;
const MIC_RELEASE = 15; // frames: the arm is up before he lets go
const MIC_FALL = 14;

export type Reaction = {
  beat: Beat;
  freezeFrom: number;
  freezeTo: number;
  reactFrame: number;
  bubbleFrom: number;
  bubbleTo: number;
};

export const bubbleChars = (line: string): number => [...line].length;

/** Frames the bubble stays: 1.8 s plus 60 ms per character. */
export const bubbleFrames = (line: string, fps: number): number => msToFrame(1800 + 60 * bubbleChars(line), fps);

export const reactionsFor = (beats: Beat[], fps: number, durationInFrames: number): Reaction[] => {
  const at = (f: number): number => Math.max(0, Math.min(durationInFrames, f));
  const out = [...beats]
    .sort((a, b) => a.at_ms - b.at_ms)
    .map((beat): Reaction => {
      const freezeFrom = at(msToFrame(beat.at_ms, fps));
      const freezeTo = beat.intensity >= 2 ? at(freezeFrom + FREEZE_FRAMES) : freezeFrom;
      const reactFrame = freezeTo;
      const bubbleFrom = at(reactFrame + BUBBLE_DELAY);
      return { beat, freezeFrom, freezeTo, reactFrame, bubbleFrom, bubbleTo: at(bubbleFrom + bubbleFrames(beat.mascot.line, fps)) };
    });
  // A bubble ends before the next reaction starts, so two bubbles never overlap.
  out.forEach((r, i) => {
    const next = out[i + 1];
    if (next) r.bubbleTo = Math.max(r.bubbleFrom, Math.min(r.bubbleTo, next.reactFrame - 1));
  });
  return out;
};

export const freezeAt = (frame: number, reactions: Reaction[]): number | null => {
  const r = reactions.find((x) => frame >= x.freezeFrom && frame < x.freezeTo);
  return r ? r.freezeFrom : null;
};

const ramp = (t: number, from: number, len: number): number => Math.max(0, Math.min(1, (t - from) / len));

/** Where a pose ends up once its own motion is over (faint is back in the box). */
const settled = (s: PoseState, pose: string): PoseState => (pose === "faint" ? { ...s, offsetX: 0, offsetY: 0, lean: 0 } : s);

/** Last frame of a faint phase: the mascot is back in the box from here, so the box clip can apply again. */
export const faintEnd = (p: Phase, fps: number): number => p.start + msToFrame(FAINT_BACK_MS, fps) + FAINT_BACK_FRAMES;

/** Per-pose motion on top of the sprung target, `t` frames after the reaction. */
const motion = (pose: string, t: number, fps: number): Partial<PoseState> => {
  const sec = t / fps;
  switch (pose) {
    case "wave": return { armR: 12 * Math.sin(sec * Math.PI * 5) };
    case "party": return { armR: 10 * Math.sin(sec * Math.PI * 6) };
    case "point": return { armR: 4 * Math.sin(sec * Math.PI * 4) };
    case "checks_watch": return { armL: 5 * Math.sin(sec * Math.PI * 6) };
    case "slow_clap": {
      // Three claps in 1.5 s, then hands rest together.
      const period = fps / 2;
      const closed = t >= 3 * period ? 1 : 0.5 + 0.5 * Math.cos((t / period) * Math.PI * 2);
      return { armL: 12 * (1 - closed), armR: -12 * (1 - closed) };
    }
    case "screaming":
      // About 6 Hz shake and 4 Hz squash-stretch: anything faster aliases at 30 fps.
      return { offsetX: 5 * Math.sin(sec * 38), squash: POSES.screaming.squash * (1 + 0.06 * Math.sin(sec * 25)) };
    case "bow": {
      const dip = Math.sin(Math.PI * ramp(t, 0, 18));
      return { squash: 1 + 0.18 * dip, offsetY: 12 * dip };
    }
    case "shocked": return { offsetY: -24 * Math.sin(Math.PI * ramp(t, 0, 12)) };
    case "sweating": return { sweat: 0.03 + 0.97 * ((t % 36) / 36) };
    case "mic_drop": {
      const fall = ramp(t, MIC_RELEASE, MIC_FALL);
      const tb = t - MIC_RELEASE - MIC_FALL;
      const bounce = tb > 0 ? 26 * Math.abs(Math.sin((Math.PI * tb) / 9)) * Math.exp(-tb / 7) : 0;
      return { propLift: POSES.mic_drop.propLift * fall * fall + bounce };
    }
    case "faint": {
      const fall = ramp(t, FAINT_ANTICIPATE, FAINT_FALL) ** 2; // ease-in: gravity
      const back = ramp(t, msToFrame(FAINT_BACK_MS, fps), FAINT_BACK_FRAMES);
      const lean = FAINT_ANTICIPATE_LEAN * ramp(t, 0, FAINT_ANTICIPATE) * (1 - fall) + FAINT_LEAN * fall;
      return { offsetX: FAINT_X * fall * (1 - back), offsetY: FAINT_Y * fall * (1 - back), lean: lean * (1 - back) };
    }
    default: return {};
  }
};

export type PoseName = keyof typeof POSES;
/** One stretch of a reaction in one pose. `start` is the frame the pose is entered. */
export type Phase = { beatId: string; pose: PoseName; start: number };

// Comeback is two jokes (spec 8): shocked, then party.
const COMEBACK_SHOCK_MS = 1200;

export const phasesOf = (r: Reaction, fps: number): Phase[] => {
  const pose = r.beat.mascot.pose;
  const out: Phase[] = [{ beatId: r.beat.beat_id, pose, start: r.reactFrame }];
  const party = r.reactFrame + msToFrame(COMEBACK_SHOCK_MS, fps);
  if (r.beat.type === "comeback" && pose === "shocked" && party < r.bubbleTo) out.push({ beatId: r.beat.beat_id, pose: "party", start: party });
  return out;
};

/** The reaction pose that is active at `frame` (bubble time), or null when the mascot is idle. */
export const phaseAt = (frame: number, reactions: Reaction[], fps: number): Phase | null => {
  const r = reactions.find((x) => frame >= x.reactFrame && frame < x.bubbleTo);
  if (!r) return null;
  return phasesOf(r, fps).filter((p) => p.start <= frame).slice(-1)[0] ?? null;
};

type Key = { start: number; pose: string; target: PoseState; react: boolean };

export const poseAt = (frame: number, reactions: Reaction[], fps: number, seed: string): PoseState => {
  const keys: Key[] = [{ start: 0, pose: "idle", target: POSES.idle, react: false }];
  for (const r of reactions) {
    for (const p of phasesOf(r, fps)) keys.push({ start: p.start, pose: p.pose, target: POSES[p.pose], react: true });
    if (r.bubbleTo > r.reactFrame) keys.push({ start: r.bubbleTo, pose: "idle", target: POSES.idle, react: false });
  }
  let k = 0;
  for (let i = 0; i < keys.length; i++) if (keys[i].start <= frame) k = i;
  const key = keys[k];
  const prev = k > 0 ? settled(keys[k - 1].target, keys[k - 1].pose) : POSES.idle;
  const p = k > 0 ? spring({ frame: frame - key.start, fps, config: MASCOT_SPRING }) : 1;
  const base = lerpPose(prev, key.target, p);
  const idle = idleAt(frame, fps, seed);
  const s: PoseState = { ...base, ...motion(key.pose, frame - key.start, fps) };
  return { ...s, squash: s.squash * (idle.squash ?? 1), offsetY: s.offsetY + (idle.offsetY ?? 0), eyeOpen: key.react && frame - key.start < NO_BLINK_FRAMES ? s.eyeOpen : Math.min(s.eyeOpen, idle.eyeOpen ?? 1) };
};
