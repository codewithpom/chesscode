import type { FC } from "react";
import { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { VideoSpec } from "../spec/schema";
import { frameToMs } from "../spec/time";
import { fontFor, useFonts } from "../theme/fonts";
import { shortsLayout, type Box } from "../theme/layout";
import { tokens } from "../theme/tokens";
import { captionPages } from "./captionPages";

// A page stays up this long after its last word, unless the next page starts first.
const LINGER_MS = 250;

// Studio: right column, x >= 1000 up to the 96 px margin, bottom-aligned under the player cards and move list.
const LONG = { left: 1000, right: 96, bottom: 96, fontSize: tokens.size.caption, lineHeight: 1.45 } as const;
// Shorts: centered over the board, inside the approved layout box (clear of the YouTube UI zones).
const SHORTS = { fontSize: 88, lineHeight: 1.3 } as const;

/** `box` (long mode only) moves the captions out of the default right column, bottom-aligned in the box. */
export const Captions: FC<{ spec: VideoSpec; mode: "long" | "shorts"; box?: Box }> = ({ spec, mode, box: override }) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
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
    ? override
      ? { left: override.x, width: override.w, bottom: height - override.y - override.h, textAlign: "left" as const }
      : { left: LONG.left, right: LONG.right, bottom: LONG.bottom, textAlign: "left" as const }
    : {
        left: shortsLayout.boxes.captions.x,
        width: shortsLayout.boxes.captions.w,
        top: shortsLayout.boxes.captions.y,
        textAlign: "center" as const,
      };

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
