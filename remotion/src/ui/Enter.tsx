import type { CSSProperties, FC, ReactNode } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { frameToMs } from "../spec/time";
import { motion } from "../theme/motion";

/** Fades and rises 16 px into place over uiEnterMs from `atMs` (absolute video ms). One element enters at a time: callers space atMs by uiEnterMs + staggerMs. */
export const Enter: FC<{ atMs: number; style?: CSSProperties; children: ReactNode }> = ({ atMs, style, children }) => {
  const { fps } = useVideoConfig();
  const ms = frameToMs(useCurrentFrame(), fps);
  const p = motion.enter(Math.min(1, Math.max(0, (ms - atMs) / motion.uiEnterMs)));
  return <div style={{ ...style, opacity: p, transform: `translateY(${(1 - p) * 16}px)` }}>{children}</div>;
};

/** Start of the i-th element of a sequence that enters one at a time. */
export const enterAt = (startMs: number, i: number): number => startMs + i * (motion.uiEnterMs + motion.staggerMs);
