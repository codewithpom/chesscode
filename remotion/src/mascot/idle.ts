import { random } from "remotion";
import { msToFrame } from "../spec/time";
import type { PoseState } from "./poseState";

// Eye openness over the 4 frames of a blink.
const BLINK = [0.5, 0, 0, 0.5] as const;

/** Blink start frames up to `frame`: gaps of 2.5 to 5 s, each from random(seed + n); the first is one gap in. */
export const blinkStarts = (frame: number, fps: number, seed: string): number[] => {
  const out: number[] = [];
  for (let i = 0, at = 0; ; i++) {
    at += msToFrame(2500 + 2500 * random(`${seed}-blink-${i}`), fps);
    if (at > frame) return out;
    out.push(at);
  }
};

/** Breathing (squash 1.00 to 1.02), bob and blink: seeded, never Math.random. Two periods so it never visibly loops. */
export const idleAt = (frame: number, fps: number, seed: string): Partial<PoseState> => {
  const t = frame / fps;
  const phase = random(`${seed}-breath`) * Math.PI * 2;
  const breath = 1 + 0.01 * (1 - Math.cos((t / 4) * Math.PI * 2 + phase));
  const bob = Math.sin((t / 3.1) * Math.PI * 2 + phase * 0.5) * 1.5;
  const starts = blinkStarts(frame, fps, seed);
  const d = starts.length ? frame - starts[starts.length - 1] : 99;
  return { squash: breath, offsetY: bob, eyeOpen: d < BLINK.length ? BLINK[d] : 1 };
};
