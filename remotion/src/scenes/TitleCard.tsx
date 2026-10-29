import type { FC } from "react";
import type { VideoSpec } from "../spec/schema";
import { fontFor, useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { Enter, enterAt } from "../ui/Enter";
import { SideChip } from "../ui/PlayerCard";
import { yearOf } from "./helpers";
import type { SceneRange } from "./timeline";

/** Quiet title card: title, the two players, the year; each enters in turn, then holds. */
export const TitleCard: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  useFonts();
  const lang = spec.language;
  const year = yearOf(spec.game.date);
  const player = (side: "white" | "black") => (
    <div style={{ display: "flex", alignItems: "center", gap: tokens.space(2) }}>
      <SideChip side={side} size={28} />
      <span>{spec.game[side].name}</span>
    </div>
  );
  return (
    <div style={{ position: "absolute", left: 96, top: 0, width: 1500, height: 1080, display: "flex", flexDirection: "column", justifyContent: "center", gap: tokens.space(4) }}>
      <Enter atMs={enterAt(range.startMs, 0)}>
        <div style={{ fontFamily: fontFor(lang, "title"), fontWeight: 600, fontSize: tokens.size.title, lineHeight: lang === "hi" ? 1.35 : 1.15, color: tokens.color.text, wordBreak: "keep-all" }}>
          {spec.youtube.title}
        </div>
      </Enter>
      <Enter atMs={enterAt(range.startMs, 1)}>
        <div style={{ display: "flex", flexDirection: "column", gap: tokens.space(1), fontFamily: fontFor(lang, "ui"), fontWeight: 500, fontSize: 40, color: tokens.color.text }}>
          {player("white")}
          {player("black")}
        </div>
      </Enter>
      {year && (
        <Enter atMs={enterAt(range.startMs, 2)}>
          <div style={{ fontFamily: tokens.font.mono, fontWeight: 500, fontSize: tokens.size.body, fontVariantNumeric: "tabular-nums", color: tokens.color.muted }}>{year}</div>
        </Enter>
      )}
    </div>
  );
};
