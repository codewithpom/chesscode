import type { FC, ReactNode } from "react";
import type { VideoSpec } from "../spec/schema";
import { boardThemes, pieceBlack, pieceBlackInk } from "../theme/boardThemes";
import { fontFor, useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";

type Player = VideoSpec["game"]["white"];

/** "GM 2850", "2850", "GM" or "" (historic players have neither). */
export const ratingLine = (p: Player): string => [p.title, p.rating].filter((v) => v !== null).join(" ");

/** Flat square in the side's piece colour (no icon). */
export const SideChip: FC<{ side: "white" | "black"; size: number; offset?: number }> = ({ side, size, offset = 0 }) => (
  <div
    style={{
      flex: "none",
      width: size,
      height: size,
      marginTop: offset,
      background: side === "white" ? boardThemes.bone_slate.light : pieceBlack,
      border: `2px solid ${side === "white" ? tokens.color.hairline : pieceBlackInk}`,
      boxSizing: "border-box",
    }}
  />
);

/**
 * One player: side chip (a flat piece-colour square), name, rating line, country code.
 * `fact` (PlayerIntro only) puts the one-line fact under the name and makes the card taller.
 * `clock` is an optional right-aligned slot for a Clock.
 */
export const PlayerCard: FC<{
  player: Player;
  side: "white" | "black";
  lang: "en" | "hi";
  fact?: boolean;
  clock?: ReactNode;
  /** Name and fact font size in px; defaults to tokens.size.body. The rating line is 28 px or 7/8 of it. */
  size?: number;
}> = ({ player, side, lang, fact = false, clock, size = tokens.size.body }) => {
  useFonts();
  const meta = [ratingLine(player), player.country].filter(Boolean).join("  ");
  return (
    <div
      style={{
        display: "flex",
        alignItems: fact ? "flex-start" : "center",
        gap: tokens.space(2),
        padding: fact ? tokens.space(3) : `0 ${tokens.space(2)}px`,
        boxSizing: "border-box",
        width: "100%",
        minHeight: 56,
        background: tokens.color.surface,
        border: `1px solid ${tokens.color.hairline}`,
        fontFamily: fontFor(lang, "ui"),
        color: tokens.color.text,
      }}
    >
      <SideChip side={side} size={size * 0.75} offset={fact ? size * 0.25 : 0} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: tokens.space(3) }}>
          <span style={{ fontSize: size, fontWeight: 600, lineHeight: 1.4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {player.name}
          </span>
          {meta && (
            <span style={{ fontFamily: tokens.font.mono, fontSize: Math.max(tokens.size.min, size * 0.875), fontVariantNumeric: "tabular-nums", color: tokens.color.muted, whiteSpace: "pre" }}>
              {meta}
            </span>
          )}
        </div>
        {fact && (
          <div style={{ marginTop: tokens.space(1), fontSize: size, lineHeight: 1.45, color: tokens.color.muted, wordBreak: "keep-all" }}>
            {player.fact}
          </div>
        )}
      </div>
      {clock}
    </div>
  );
};
