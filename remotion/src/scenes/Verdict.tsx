import type { FC } from "react";
import type { VideoSpec } from "../spec/schema";
import { fontFor, useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { Enter, enterAt } from "../ui/Enter";
import { PlayerCard } from "../ui/PlayerCard";
import { moveLabel, resultText } from "./helpers";
import { StudioBoard } from "./StudioBoard";
import { strings } from "./strings";
import type { SceneRange } from "./timeline";

const COL = { x: 1000, w: 824 } as const;
const mono = (size: number) =>
  ({ fontFamily: tokens.font.mono, fontWeight: 500, fontSize: size, fontVariantNumeric: "tabular-nums", color: tokens.color.text }) as const;

/** Result, the turning-point position with its move highlighted (no arrows), and accuracy per side. */
export const Verdict: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  useFonts();
  const t = strings[spec.language];
  const tp = spec.plies[spec.verdict.turning_point_ply - 1];
  const lab = { fontFamily: fontFor(spec.language, "ui"), fontSize: tokens.size.label, color: tokens.color.muted, marginBottom: tokens.space(1) } as const;
  return (
    <>
      <StudioBoard spec={spec} atMs={tp.show_at_ms + 400} hideArrows showEval={false} />
      <Enter atMs={enterAt(range.startMs, 0)} style={{ position: "absolute", left: COL.x, top: 112, width: COL.w }}>
        <div style={{ ...mono(96), lineHeight: 1.1 }}>{resultText(spec.game.result)}</div>
      </Enter>
      <Enter atMs={enterAt(range.startMs, 1)} style={{ position: "absolute", left: COL.x, top: 240, width: COL.w }}>
        <div style={lab}>{t.turningPoint}</div>
        <div style={mono(48)}>{moveLabel(tp)}</div>
      </Enter>
      <Enter atMs={enterAt(range.startMs, 2)} style={{ position: "absolute", left: COL.x, top: 368, width: COL.w }}>
        <div style={lab}>{t.accuracy}</div>
        <div style={{ display: "flex", flexDirection: "column", gap: tokens.space(1) }}>
          {(["white", "black"] as const).map((side) => (
            <PlayerCard
              key={side}
              player={spec.game[side]}
              side={side}
              lang={spec.language}
              clock={<span style={mono(tokens.size.body)}>{spec.verdict.accuracy[side].toFixed(1)}</span>}
            />
          ))}
        </div>
      </Enter>
    </>
  );
};
