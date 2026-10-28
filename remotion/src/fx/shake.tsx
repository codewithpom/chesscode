import type { FC, ReactNode } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Beat } from "../spec/schema";
import { activeWindow, fxWindows, type FxWindow } from "./windows";

const MAX_PX = 6;

/** Board translate in px: alternates every frame, decays linearly to 0 over the window, never above 6 px. Zero outside it. */
export const shakeOffset = (frame: number, windows: FxWindow[]): { x: number; y: number } => {
  const w = activeWindow(windows, "board_shake", frame);
  if (!w) return { x: 0, y: 0 };
  const t = frame - w.from;
  const amp = MAX_PX * (1 - t / (w.to - w.from));
  return { x: t % 2 === 0 ? amp : -amp, y: t % 3 === 0 ? amp / 2 : -amp / 2 };
};

/** Translates its children by the shake offset. Reads the absolute frame. */
export const ShakeBox: FC<{ beats: Beat[]; template: "studio" | "shorts"; children: ReactNode }> = ({ beats, template, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { x, y } = shakeOffset(frame, fxWindows(beats, fps, { template }));
  return <div style={{ transform: `translate(${x}px, ${y}px)` }}>{children}</div>;
};
