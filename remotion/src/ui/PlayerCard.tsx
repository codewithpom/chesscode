import type { FC, ReactNode } from "react";
import type { VideoSpec } from "../spec/schema";
import { boardThemes, pieceBlack, pieceBlackInk } from "../theme/boardThemes";
import { fontFor, useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";

type Player = VideoSpec["game"]["white"];

/** "GM 2850", "2850", "GM" or "" (historic players have neither). */
export const ratingLine = (p: Player): string => [p.title, p.rating].filter((v) => v !== null).join(" ");

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
}> = ({ player, side, lang, fact = false, clock }) => {
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
      <div
        style={{
          flex: "none",
          width: 24,
          height: 24,
          marginTop: fact ? 8 : 0,
          background: side === "white" ? boardThemes.bone_slate.light : pieceBlack,
          border: `2px solid ${side === "white" ? tokens.color.hairline : pieceBlackInk}`,
          boxSizing: "border-box",
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: tokens.space(3) }}>
          <span style={{ fontSize: tokens.size.body, fontWeight: 600, lineHeight: 1.4, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {player.name}
          </span>
          {meta && (
            <span style={{ fontFamily: tokens.font.mono, fontSize: tokens.size.min, fontVariantNumeric: "tabular-nums", color: tokens.color.muted, whiteSpace: "pre" }}>
              {meta}
            </span>
          )}
        </div>
        {fact && (
          <div style={{ marginTop: tokens.space(1), fontSize: tokens.size.body, lineHeight: 1.45, color: tokens.color.muted, wordBreak: "keep-all" }}>
            {player.fact}
          </div>
        )}
      </div>
      {clock}
    </div>
  );
};
