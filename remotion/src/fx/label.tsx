import type { FC } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Beat } from "../spec/schema";
import { frameToMs } from "../spec/time";
import type { Box } from "../theme/layout";
import { LabelPlate } from "../ui/ChapterCard";
import { activeWindow, fxWindows } from "./windows";

// The only fixed UI string the effects draw. Hindi keeps the chess word "theory" in English-script Devanagari,
// the way the channel's Hindi lines do (docs/SPEC.md section 8); the owner should confirm the wording.
export const OUT_OF_THEORY = { en: "Out of theory", hi: "थ्योरी से बाहर" } as const;

/** "Out of theory" plate in `box` while the window is on. Reads the absolute frame. */
export const OutOfTheoryLabel: FC<{ beats: Beat[]; template: "studio" | "shorts"; lang: "en" | "hi"; box: Box }> = ({
  beats,
  template,
  lang,
  box,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const w = activeWindow(fxWindows(beats, fps, { template }), "out_of_theory_label", frame);
  if (!w) return null;
  return (
    <div style={{ position: "absolute", left: box.x, top: box.y, width: box.w, height: box.h }}>
      <LabelPlate startMs={frameToMs(w.from, fps)} endMs={frameToMs(w.to, fps)} lang={lang} text={OUT_OF_THEORY[lang]} />
    </div>
  );
};
