// 9:16 Short (docs/SPEC.md section 5): hook text from frame 0, one beat, captions above the board, the mascot
// box below it. Everything sits in theme/layout.ts `shortsLayout` (nothing in the right 120 px or bottom 340 px).
// The last 10 frames ease the board back to the first frame's position so the loop holds.
import type { FC } from "react";
import { AbsoluteFill, CalculateMetadataFunction, useCurrentFrame, useVideoConfig } from "remotion";
import { MusicBed } from "../audio/MusicBed";
import { NarrationTrack } from "../audio/NarrationTrack";
import { Sfx } from "../audio/Sfx";
import { BoardView } from "../board/Board";
import { boardStateAt } from "../board/boardState";
import { blendStates, loopProgress } from "../board/loopBlend";
import { buildPositions } from "../board/positions";
import { BoardFx, boardMsAt, fxWindows, OutOfTheoryLabel, ShakeBox } from "../fx";
import { evalSpec } from "../scenes/StudioBoard";
import { MascotSlot } from "../scenes/MascotSlot";
import { SUPPORTED_MAJOR, VideoSpec } from "../spec/schema";
import { frameToMs, msToFrame } from "../spec/time";
import { fontFor, useFonts } from "../theme/fonts";
import { shortsLayout } from "../theme/layout";
import { tokens } from "../theme/tokens";
import { Captions } from "../ui/Captions";
import { EvalBar } from "../ui/EvalBar";

const HOOK_MS = 1000;
const { captions, evalBar, board, mascot, fileLabels } = shortsLayout.boxes;
// Out-of-theory plate: under the board's file labels, above the mascot box's usable area.
const labelBox = { x: board.x, y: fileLabels.y + fileLabels.h + 8, w: board.w, h: 56 } as const;

export const calculateShortsMetadata: CalculateMetadataFunction<VideoSpec> = ({ props }) => {
  const major = Number(props.spec_version.split(".")[0]);
  if (major !== SUPPORTED_MAJOR) throw new Error(`spec_version ${props.spec_version} not supported (major ${SUPPORTED_MAJOR})`);
  if (props.template !== "shorts") throw new Error(`ShortsVideo needs template "shorts", got "${props.template}"`);
  const { width, height, fps } = props.format;
  return { durationInFrames: msToFrame(props.duration_ms, fps), width, height, fps };
};

/** Board with shake, replay/freeze time, overlay fx and the closing ease back to the opening position. */
const ShortsBoard: FC<{ spec: VideoSpec }> = ({ spec }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const positions = buildPositions(spec.game.pgn);
  const windows = fxWindows(spec.beats, fps, { template: "shorts", plies: spec.plies });
  const boardFrame = msToFrame(boardMsAt(frame, fps, windows, frameToMs(frame, fps)), fps);
  const real = boardStateAt(boardFrame, fps, spec.plies, positions);
  const t = loopProgress(frame, durationInFrames);
  const state = t > 0 ? blendStates(real, boardStateAt(0, fps, spec.plies, positions), t) : real;
  return (
    <div style={{ position: "absolute", left: board.x, top: board.y, width: board.w, height: board.h }}>
      <ShakeBox beats={spec.beats} template="shorts">
        <div style={{ position: "relative", width: board.w, height: board.h }}>
          <BoardView state={state} size={board.w} orientation={spec.board.orientation} theme={spec.board.theme} />
          {t === 0 && <BoardFx spec={spec} size={board.w} orientation={spec.board.orientation} template="shorts" />}
        </div>
      </ShakeBox>
    </div>
  );
};

export const ShortsVideo: FC<VideoSpec> = (spec) => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hook = frameToMs(frame, fps) < HOOK_MS;
  const hi = spec.language === "hi";
  return (
    <AbsoluteFill style={{ backgroundColor: tokens.color.bg }}>
      <ShortsBoard spec={spec} />
      <div style={{ position: "absolute", left: evalBar.x, top: evalBar.y }}>
        <EvalBar spec={evalSpec(spec, "shorts")} orientation="horizontal" length={evalBar.w} thickness={evalBar.h} labelSize={shortsLayout.evalLabelSize} />
      </div>
      {hook ? (
        // The hook owns the captions box for the first second, from frame 0; captions take over after it.
        <div
          style={{
            position: "absolute",
            left: captions.x,
            top: captions.y,
            width: captions.w,
            height: captions.h,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            textAlign: "center",
            fontFamily: fontFor(spec.language, "title"),
            fontWeight: 600,
            fontSize: hi ? 44 : 52,
            lineHeight: hi ? 1.25 : 1.08,
            color: tokens.color.text,
            wordBreak: "keep-all",
          }}
        >
          {spec.cold_open.hook}
        </div>
      ) : (
        <Captions spec={spec} mode="shorts" />
      )}
      <OutOfTheoryLabel beats={spec.beats} template="shorts" lang={spec.language} box={labelBox} />
      <MascotSlot spec={spec} box={mascot} />
      <NarrationTrack segments={spec.narration} />
      <MusicBed music={spec.music} narration={spec.narration} />
      <Sfx beats={spec.beats} />
    </AbsoluteFill>
  );
};
