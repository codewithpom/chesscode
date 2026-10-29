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
export const BUBBLE_EXIT_FRAMES = 6;
const LAST_WORD_HOLD_MS = 500;

/**
 * Frame at which each word appears: when its first character is typed, so the first word shows on `from`. Types at
 * 12 characters per second, faster when needed so the last word is up half a second before the exit starts at `to`.
 */
const wordFrames = (line: string, from: number, fps: number, to = Infinity): number[] => {
  let chars = 0;
  const starts = line.split(" ").map((w) => {
    const at = chars;
    chars += [...w].length + 1;
    return at;
  });
  const budget = (to - BUBBLE_EXIT_FRAMES - msToFrame(LAST_WORD_HOLD_MS, fps) - from) / fps;
  const cps = Math.max(CHARS_PER_SECOND, starts[starts.length - 1] / budget);
  return starts.map((c) => from + msToFrame(budget > 0 ? (c / cps) * 1000 : 0, fps));
};

/** The part of `line` typed by `frame`, always whole words. Pass `to` (bubble end frame) to type fast enough to finish. */
export const typedText = (line: string, frame: number, from: number, fps: number, to?: number): string => {
  const done = wordFrames(line, from, fps, to).filter((f) => frame >= f).length;
  return line.split(" ").slice(0, done).join(" ");
};

/** Frame at which the last word has appeared (the mouth stops flapping). */
export const typingEnd = (line: string, from: number, fps: number, to?: number): number =>
  wordFrames(line, from, fps, to).slice(-1)[0] ?? from;

export type Blip = { frame: number; sample: 1 | 2 | 3 | 4 | 5 | 6 };

/** One voice blip per word, on the frame the word appears; the sample is seeded. */
export const blipFrames = (line: string, from: number, fps: number, seed: string, to?: number): Blip[] =>
  wordFrames(line, from, fps, to).map((frame, i) => ({ frame, sample: (1 + Math.floor(random(`${seed}-blip-${i}`) * 6)) as Blip["sample"] }));

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
  const outP = interpolate(frame, [to - BUBBLE_EXIT_FRAMES, to], [0, 1], { easing: motion.exit, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const t = inP * (1 - outP);
  const text = {
    fontFamily: fontFor(language, "ui"), fontSize: BUBBLE_FONT, fontWeight: 500, lineHeight: 1.3, color: P.ink,
    gridArea: "1 / 1", overflowWrap: "normal", wordBreak: "normal", hyphens: "manual",
  } as const;
  // Shrinks to the line (the hidden full text fixes the size so it does not grow while typing), right-aligned to the
  // mascot, centred on the box; max sizes keep it inside `box`.
  return (
    <div style={{ position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h, display: "flex", justifyContent: "flex-end", alignItems: "center" }}>
      <div style={{ display: "flex", alignItems: "center", maxWidth: box.w, maxHeight: box.h, opacity: t, transform: `scale(${0.92 + 0.08 * t})`, transformOrigin: "100% 50%" }}>
        <div
          lang={language}
          style={{
            boxSizing: "border-box", padding: "16px 24px", overflow: "hidden", maxWidth: box.w - BUBBLE_TAIL, maxHeight: box.h,
            background: P.body, border: `4px solid ${P.ink}`, borderRadius: 24, display: "grid", alignContent: "center",
          }}
        >
          <div style={{ ...text, visibility: "hidden" }}>{line}</div>
          <div style={text}>{typedText(line, frame, from, fps, to)}</div>
        </div>
        <svg width={BUBBLE_TAIL} height={40} style={{ flex: "none", marginLeft: -4 }}>
          <path d={`M0,2 L${BUBBLE_TAIL - 2},20 L0,38`} fill={P.body} stroke={P.ink} strokeWidth={4} strokeLinejoin="round" />
          <rect x={0} y={5} width={4} height={30} fill={P.body} />
        </svg>
      </div>
    </div>
  );
};
