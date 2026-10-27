// Placeholder long-form composition: proves the contract end to end (props -> metadata
// -> audio) and gives M1 a render to time. M5 replaces the body with the Studio scenes.
import { AbsoluteFill, CalculateMetadataFunction, useCurrentFrame, useVideoConfig } from "remotion";
import { NarrationTrack } from "../audio/NarrationTrack";
import { SUPPORTED_MAJOR, VideoSpec } from "../spec/schema";
import { frameToMs, msToFrame } from "../spec/time";

export const calculateStudioMetadata: CalculateMetadataFunction<VideoSpec> = ({ props }) => {
  const major = Number(props.spec_version.split(".")[0]);
  if (major !== SUPPORTED_MAJOR) {
    throw new Error(`spec_version ${props.spec_version} not supported (major ${SUPPORTED_MAJOR})`);
  }
  const { width, height, fps } = props.format;
  return { durationInFrames: msToFrame(props.duration_ms, fps), width, height, fps };
};

export const StudioVideo: React.FC<VideoSpec> = (spec) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const now = frameToMs(frame, fps);
  const shown = spec.plies.filter((p) => p.show_at_ms <= now);
  const last = shown[shown.length - 1];
  return (
    <AbsoluteFill style={{ backgroundColor: "#0F1115", color: "#ECEEF2", fontFamily: "monospace", fontSize: 48, padding: 96 }}>
      <div>{spec.game.white.name} vs {spec.game.black.name}</div>
      <div style={{ marginTop: 48 }}>{last ? `${Math.ceil(last.ply / 2)}${last.ply % 2 ? "." : "..."} ${last.san}` : "-"}</div>
      <NarrationTrack segments={spec.narration} />
    </AbsoluteFill>
  );
};
