// 16:9 long-form composition: the Studio scene sequence (docs/SPEC.md section 5) cut by scenes/timeline.ts.
// Scenes are hard cuts. Each runs in a Sequence whose frame is shifted back to the video's own, so the shared
// pieces (Board, EvalBar, Captions, MoveList, fx) can all read one absolute frame.
import type { FC } from "react";
import { useMemo } from "react";
import { AbsoluteFill, CalculateMetadataFunction, Sequence, useVideoConfig } from "remotion";
import { MusicBed } from "../audio/MusicBed";
import { NarrationTrack } from "../audio/NarrationTrack";
import { Sfx } from "../audio/Sfx";
import { ColdOpen } from "../scenes/ColdOpen";
import { KeyMoment } from "../scenes/KeyMoment";
import { Outro } from "../scenes/Outro";
import { PlayerIntro } from "../scenes/PlayerIntro";
import { Playback } from "../scenes/Playback";
import { TitleCard } from "../scenes/TitleCard";
import { sceneRanges, type SceneRange } from "../scenes/timeline";
import { Verdict } from "../scenes/Verdict";
import { SUPPORTED_MAJOR, VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { Captions } from "../ui/Captions";

export const calculateStudioMetadata: CalculateMetadataFunction<VideoSpec> = ({ props }) => {
  const major = Number(props.spec_version.split(".")[0]);
  if (major !== SUPPORTED_MAJOR) {
    throw new Error(`spec_version ${props.spec_version} not supported (major ${SUPPORTED_MAJOR})`);
  }
  const { width, height, fps } = props.format;
  return { durationInFrames: msToFrame(props.duration_ms, fps), width, height, fps };
};

const SceneFor: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  switch (range.kind) {
    case "cold_open": return <ColdOpen spec={spec} range={range} />;
    case "title": return <TitleCard spec={spec} range={range} />;
    case "player_intro": return <PlayerIntro spec={spec} range={range} />;
    case "playback": return <Playback spec={spec} range={range} />;
    case "key_moment": return <KeyMoment spec={spec} range={range} />;
    case "verdict": return <Verdict spec={spec} range={range} />;
    case "outro": return <Outro spec={spec} />;
  }
};

export const StudioVideo: FC<VideoSpec> = (spec) => {
  useFonts();
  const { fps } = useVideoConfig();
  const ranges = useMemo(() => sceneRanges(spec), [spec]);
  return (
    <AbsoluteFill style={{ backgroundColor: tokens.color.bg }}>
      {ranges.map((r) => {
        const from = msToFrame(r.startMs, fps);
        return (
          <Sequence key={`${r.kind}-${r.startMs}`} from={from} durationInFrames={Math.max(1, msToFrame(r.endMs, fps) - from)} layout="none">
            <Sequence from={-from} layout="none">
              <SceneFor spec={spec} range={r} />
            </Sequence>
          </Sequence>
        );
      })}
      <Captions spec={spec} mode="long" />
      <NarrationTrack segments={spec.narration} />
      <MusicBed music={spec.music} narration={spec.narration} />
      <Sfx beats={spec.beats} />
    </AbsoluteFill>
  );
};
