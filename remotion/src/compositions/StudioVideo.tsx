// Placeholder long-form composition: proves the contract end to end (props -> metadata
// -> audio) and gives M1 a render to time. M5 replaces the body with the Studio scenes.
import { AbsoluteFill, CalculateMetadataFunction } from "remotion";
import { Board } from "../board/Board";
import { useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";
import { Captions } from "../ui/Captions";
import { EvalBar } from "../ui/EvalBar";
import { NarrationTrack } from "../audio/NarrationTrack";
import { SUPPORTED_MAJOR, VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";

export const calculateStudioMetadata: CalculateMetadataFunction<VideoSpec> = ({ props }) => {
  const major = Number(props.spec_version.split(".")[0]);
  if (major !== SUPPORTED_MAJOR) {
    throw new Error(`spec_version ${props.spec_version} not supported (major ${SUPPORTED_MAJOR})`);
  }
  const { width, height, fps } = props.format;
  return { durationInFrames: msToFrame(props.duration_ms, fps), width, height, fps };
};

export const StudioVideo: React.FC<VideoSpec> = (spec) => {
  useFonts();
  // Placeholder layout (spec section 6 numbers) so render timing reflects the real drawing load;
  // M5 replaces this body with the Studio scenes.
  return (
    <AbsoluteFill style={{ backgroundColor: tokens.color.bg }}>
      <div style={{ position: "absolute", left: 96 + 24 + 16, top: 140 }}>
        <Board spec={spec} size={800} />
      </div>
      <div style={{ position: "absolute", left: 96, top: 140 }}>
        <EvalBar spec={spec} orientation="vertical" length={800} thickness={24} />
      </div>
      <Captions spec={spec} mode="long" />
      <NarrationTrack segments={spec.narration} />
    </AbsoluteFill>
  );
};
