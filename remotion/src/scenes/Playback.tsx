import type { FC } from "react";
import { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { activeWindow, boardMsAt, fxWindows, OutOfTheoryLabel } from "../fx";
import type { VideoSpec } from "../spec/schema";
import { frameToMs } from "../spec/time";
import { useFonts } from "../theme/fonts";
import { studioLayout } from "../theme/layout";
import { templateFx } from "../theme/templates";
import { ChapterCard } from "../ui/ChapterCard";
import { Clock } from "../ui/Clock";
import { MoveList } from "../ui/MoveList";
import { PlayerCard } from "../ui/PlayerCard";
import { clockFor, currentPlyAt } from "./helpers";
import { MascotSlot } from "./MascotSlot";
import { StudioBoard } from "./StudioBoard";
import { chapterCardsFor, type SceneRange } from "./timeline";

const { label, cards, moveList, mascot } = studioLayout.boxes;
const CHAPTER_CARD_MS = 3000;
const ROW = 56;

/** The main scene: board with beat effects, eval bar, move list, player cards with clocks, chapter cards. */
export const Playback: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowMs = frameToMs(frame, fps);
  const windows = useMemo(() => fxWindows(spec.beats, fps, { template: "studio", plies: spec.plies }), [spec.beats, spec.plies, fps]);
  const boardMs = boardMsAt(frame, fps, windows, nowMs);
  const ply = currentPlyAt(spec.plies, frame, fps) ?? 0;

  const theoryLabel = !!activeWindow(windows, "out_of_theory_label", frame);
  const chapters = chapterCardsFor(spec);
  const card = chapters
    .map((c, i) => ({ ...c, index: i + 2, endMs: Math.min(c.startMs + CHAPTER_CARD_MS, range.endMs) }))
    .find((c) => nowMs >= c.startMs && nowMs < c.endMs);

  // Top card is the player at the far side of the board.
  const sides = spec.board.orientation === "white" ? (["black", "white"] as const) : (["white", "black"] as const);
  const clockSlot = (side: "white" | "black") => {
    const ms = clockFor(spec.plies, side, ply);
    if (ms === null) return undefined;
    const moverSide = (w: { beat: { ply: number } }) => (w.beat.ply % 2 === 1 ? "white" : "black");
    const red = windows.some((w) => w.fx === "clock_red" && moverSide(w) === side && frame >= w.from && frame < w.to);
    const pulse = activeWindow(windows, "clock_pulse", frame);
    const pulsing = pulse && moverSide(pulse) === side ? Math.sin((Math.PI * (frame - pulse.from)) / 12) ** 2 : 0;
    return <Clock ms={ms} red={red} pulse={pulsing} />;
  };

  return (
    <>
      <StudioBoard spec={spec} atMs={boardMs} fx />
      <div style={{ position: "absolute", left: label.x, top: label.y, width: label.w, height: label.h }}>
        {card && !theoryLabel && (
          <ChapterCard title={card.title} index={card.index} startMs={card.startMs} endMs={card.endMs} lang={spec.language} />
        )}
      </div>
      <OutOfTheoryLabel beats={spec.beats} template="studio" lang={spec.language} box={label} />
      <div style={{ position: "absolute", left: cards.x, top: cards.y, width: cards.w, display: "flex", flexDirection: "column", gap: cards.h - 2 * ROW }}>
        {sides.map((side) => (
          <div key={side} style={{ height: ROW }}>
            <PlayerCard player={spec.game[side]} side={side} lang={spec.language} clock={clockSlot(side)} />
          </div>
        ))}
      </div>
      <MoveList spec={spec} box={moveList} underline={templateFx.studio.move_underline} />
      <MascotSlot spec={spec} box={mascot} />
    </>
  );
};
