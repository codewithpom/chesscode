import { interpolate, random, useCurrentFrame, useVideoConfig } from "remotion";
import { msToFrame } from "../spec/time";
import { fontFor, useFonts } from "../theme/fonts";
import { motion } from "../theme/motion";
import type { Box } from "../theme/layout";
import { size } from "../theme/tokens";
import { P } from "./parts/kit";

/** Type-on speed. */
export const CHARS_PER_SECOND = 12;
export const BUBBLE_FONT = size.min + 2; // 30 px, never below 28
export const BUBBLE_TAIL = 20;
const EXIT_FRAMES = 6;

/** Frame at which each word has been fully typed (a word never shows partially, so Devanagari clusters never split). */
const wordFrames = (line: string, from: number, fps: number): number[] => {
  let chars = 0;
  return line.split(" ").map((w, i) => {
    chars += [...w].length + (i > 0 ? 1 : 0);
    return from + msToFrame((chars / CHARS_PER_SECOND) * 1000, fps);
  });
};

/** The part of `line` typed by `frame`, always whole words. */
export const typedText = (line: string, frame: number, from: number, fps: number): string => {
  const done = wordFrames(line, from, fps).filter((f) => frame >= f).length;
  return line.split(" ").slice(0, done).join(" ");
};

/** Frame at which the last word has appeared (the mouth stops flapping). */
export const typingEnd = (line: string, from: number, fps: number): number => wordFrames(line, from, fps).slice(-1)[0] ?? from;

export type Blip = { frame: number; sample: 1 | 2 | 3 | 4 | 5 | 6 };

/** One voice blip per word, on the frame the word appears; the sample is seeded. */
export const blipFrames = (line: string, from: number, fps: number, seed: string): Blip[] =>
  wordFrames(line, from, fps).map((frame, i) => ({ frame, sample: (1 + Math.floor(random(`${seed}-blip-${i}`) * 6)) as Blip["sample"] }));

/** Speech bubble drawn inside `box` (tail included), pointing right at the mascot. Visible from `from` to `to` (frames). */
export const SpeechBubble: React.FC<{ line: string; from: number; to: number; box: Box; language: "en" | "hi" }> = ({
  line, from, to, box, language,
}) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (frame < from || frame >= to) return null;
  const enterF = msToFrame(motion.uiEnterMs, fps);
  const inP = interpolate(frame, [from, from + enterF], [0, 1], { easing: motion.enter, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const outP = interpolate(frame, [to - EXIT_FRAMES, to], [0, 1], { easing: motion.exit, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const t = inP * (1 - outP);
  const w = box.w - BUBBLE_TAIL;
  const text = {
    fontFamily: fontFor(language, "ui"), fontSize: BUBBLE_FONT, fontWeight: 500, lineHeight: 1.3, color: P.ink,
    gridArea: "1 / 1", overflowWrap: "normal", wordBreak: "normal", hyphens: "manual",
  } as const;
  return (
    <div style={{ position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h, opacity: t, transform: `scale(${0.92 + 0.08 * t})`, transformOrigin: "100% 70%" }}>
      <div
        lang={language}
        style={{
          position: "absolute", left: 0, top: 0, width: w, height: box.h, boxSizing: "border-box", padding: "16px 24px", overflow: "hidden",
          background: P.body, border: `4px solid ${P.ink}`, borderRadius: 24, display: "grid", alignContent: "center",
        }}
      >
        <div style={{ ...text, visibility: "hidden" }}>{line}</div>
        <div style={text}>{typedText(line, frame, from, fps)}</div>
      </div>
      <svg width={BUBBLE_TAIL + 4} height={40} style={{ position: "absolute", left: w - 4, top: box.h * 0.7 - 20 }}>
        <path d={`M0,2 L${BUBBLE_TAIL},20 L0,38 Z`} fill={P.body} stroke={P.ink} strokeWidth={4} strokeLinejoin="round" />
        <rect x={0} y={5} width={4} height={30} fill={P.body} />
      </svg>
    </div>
  );
};
