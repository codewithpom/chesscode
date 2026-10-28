import { spring } from "remotion";
import type { Beat } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { uiSpring } from "../theme/motion";
import { idleAt } from "./idle";
import { POSES } from "./poses";
import { lerpPose, type PoseState } from "./poseState";

// Comic timing (docs/SPEC.md section 8): freeze 6 frames, react on frame 7, bubble text from frame 10.
const FREEZE_FRAMES = 6;
const BUBBLE_DELAY = 3; // frames from the reaction to the bubble (frame 7 -> frame 10)
const FAINT_OUT = 12;
const FAINT_BACK_MS = 1500;
const FAINT_X = POSES.faint.offsetX;
const FAINT_LEAN = POSES.faint.lean;
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
const settled = (s: PoseState, pose: string): PoseState => (pose === "faint" ? { ...s, offsetX: 0, lean: 0 } : s);

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
      return { offsetX: 3 * Math.sin(sec * 90), squash: POSES.screaming.squash * (1 + 0.04 * Math.sin(sec * 70)) };
    case "shocked": return { offsetY: -24 * Math.sin(Math.PI * ramp(t, 0, 12)) };
    case "sweating": return { sweat: 0.03 + 0.97 * ((t % 36) / 36) };
    case "mic_drop": {
      const fall = ramp(t, 6, MIC_FALL);
      const tb = t - 6 - MIC_FALL;
      const bounce = tb > 0 ? 26 * Math.abs(Math.sin((Math.PI * tb) / 9)) * Math.exp(-tb / 7) : 0;
      return { propLift: POSES.mic_drop.propLift * fall * fall + bounce };
    }
    case "faint": {
      const back = ramp(t, msToFrame(FAINT_BACK_MS, fps), FAINT_OUT);
      const k = ramp(t, 0, FAINT_OUT) * (1 - back);
      return { offsetX: FAINT_X * k, lean: FAINT_LEAN * k };
    }
    default: return {};
  }
};

type Key = { start: number; pose: string; target: PoseState };

export const poseAt = (frame: number, reactions: Reaction[], fps: number, seed: string): PoseState => {
  const keys: Key[] = [{ start: 0, pose: "idle", target: POSES.idle }];
  for (const r of reactions) {
    keys.push({ start: r.reactFrame, pose: r.beat.mascot.pose, target: POSES[r.beat.mascot.pose] });
    if (r.bubbleTo > r.reactFrame) keys.push({ start: r.bubbleTo, pose: "idle", target: POSES.idle });
  }
  let k = 0;
  for (let i = 0; i < keys.length; i++) if (keys[i].start <= frame) k = i;
  const key = keys[k];
  const prev = k > 0 ? settled(keys[k - 1].target, keys[k - 1].pose) : POSES.idle;
  const p = k > 0 ? spring({ frame: frame - key.start, fps, config: uiSpring }) : 1;
  const base = lerpPose(prev, key.target, p);
  const idle = idleAt(frame, fps, seed);
  const s: PoseState = { ...base, ...motion(key.pose, frame - key.start, fps) };
  return { ...s, squash: s.squash * (idle.squash ?? 1), offsetY: s.offsetY + (idle.offsetY ?? 0), eyeOpen: Math.min(s.eyeOpen, idle.eyeOpen ?? 1) };
};
