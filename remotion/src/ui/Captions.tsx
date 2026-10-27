import type { FC } from "react";
import { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { VideoSpec } from "../spec/schema";
import { frameToMs } from "../spec/time";
import { fontFor, useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { captionPages } from "./captionPages";

// A page stays up this long after its last word, unless the next page starts first.
const LINGER_MS = 250;

// Studio: right column, x >= 1000 up to the 96 px margin, bottom-aligned under the player cards and move list.
const LONG = { left: 1000, right: 96, bottom: 96, fontSize: tokens.size.caption, lineHeight: 1.45 } as const;
// Shorts: centered above the board; 120 px kept free at both sides (YouTube UI covers the right).
const SHORTS = { top: 120, side: 120, fontSize: 88, lineHeight: 1.3 } as const;

export const Captions: FC<{ spec: VideoSpec; mode: "long" | "shorts" }> = ({ spec, mode }) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pages = useMemo(() => captionPages(spec.narration, mode), [spec.narration, mode]);
  const nowMs = frameToMs(frame, fps);

  let idx = -1;
  for (let i = 0; i < pages.length; i++) if (pages[i].startMs <= nowMs) idx = i;
  if (idx < 0) return null;
  const page = pages[idx];
  const lastEnd = page.tokens[page.tokens.length - 1].toMs;
  if (nowMs > lastEnd + LINGER_MS) return null;

  let current = 0;
  page.tokens.forEach((t, i) => {
    if (t.fromMs <= nowMs) current = i;
  });

  const long = mode === "long";
  const box = long
    ? { left: LONG.left, right: LONG.right, bottom: LONG.bottom, textAlign: "left" as const }
    : { left: SHORTS.side, right: SHORTS.side, top: SHORTS.top, textAlign: "center" as const };

  return (
    <div
      style={{
        position: "absolute",
        ...box,
        fontFamily: fontFor(spec.language, "ui"),
        fontWeight: 500,
        fontSize: long ? LONG.fontSize : SHORTS.fontSize,
        lineHeight: long ? LONG.lineHeight : SHORTS.lineHeight,
        whiteSpace: "pre-wrap", // leading spaces are the only break points
        wordBreak: "keep-all", // never break inside a word or Devanagari cluster
        overflowWrap: "normal",
      }}
    >
      {page.tokens.map((t, i) => (
        <span key={i} style={{ color: i === current ? tokens.color.text : tokens.color.muted }}>
          {t.text}
        </span>
      ))}
    </div>
  );
};
