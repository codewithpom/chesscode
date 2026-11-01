import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { frameToMs } from "../spec/time";
import { fontFor, useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { plateStyle } from "./plate";

/**
 * Shared plate for the label slot (top-left of the right column). Reads the absolute frame, so mount it
 * where the frame is the video's own; shown from startMs to endMs.
 */
export const LabelPlate: FC<{ startMs: number; endMs: number; lang: "en" | "hi"; index?: number; text: string }> = ({
  startMs,
  endMs,
  lang,
  index,
  text,
}) => {
  useFonts();
  const { fps } = useVideoConfig();
  const ms = frameToMs(useCurrentFrame(), fps);
  return (
    <div
      style={{
        ...plateStyle(ms, startMs, endMs),
        display: "flex",
        alignItems: "center",
        gap: tokens.space(2),
        boxSizing: "border-box",
        width: "100%",
        height: "100%",
        padding: `0 ${tokens.space(2)}px`,
        background: tokens.color.surface,
        border: `1px solid ${tokens.color.hairline}`,
        color: tokens.color.text,
      }}
    >
      {index !== undefined && (
        <span style={{ fontFamily: tokens.font.mono, fontWeight: 500, fontSize: tokens.size.body, fontVariantNumeric: "tabular-nums", color: tokens.color.muted }}>
          {String(index).padStart(2, "0")}
        </span>
      )}
      <span
        style={{
          fontFamily: fontFor(lang, "title"),
          fontWeight: 600,
          fontSize: tokens.size.body,
          lineHeight: 1.3,
          wordBreak: "keep-all",
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
        }}
      >
        {text}
      </span>
    </div>
  );
};

/** A chapter title between phases of the game; `index` is the chapter number (2 for the first card). */
export const ChapterCard: FC<{ title: string; index: number; startMs: number; endMs: number; lang: "en" | "hi" }> = ({
  title,
  index,
  ...rest
}) => <LabelPlate {...rest} index={index} text={title} />;
