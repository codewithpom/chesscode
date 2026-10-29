// Review reel: 20 s of synthetic beats on a plain background with a mock board, showing the comic timing
// (docs/SPEC.md section 8): 6-frame freeze, reaction on frame 7, bubble from frame 10, back to idle.
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import fixture from "../../../spec/fixtures/cc-2026-0001-en/video_spec.json";
import { MascotLayer, freezeAt, reactionsFor } from "../mascot";
import { VideoSpec, type Beat } from "../spec/schema";
import { useFonts } from "../theme/fonts";
import type { Box } from "../theme/layout";
import { tokens } from "../theme/tokens";

const base = VideoSpec.parse(fixture);
const beat = (id: string, type: Beat["type"], at_ms: number, intensity: 1 | 2 | 3, pose: Beat["mascot"]["pose"], line: string): Beat => ({
  beat_id: id, type, ply: 10, at_ms, intensity, mascot: { pose, line }, fx: [], sfx: null,
});

// Closer together than the 20 s pacing minimum on purpose: the reel shows all six reactions in 20 s.
export const REEL_SPEC: VideoSpec = {
  ...base,
  duration_ms: 20_000,
  beats: [
    beat("r-1", "blunder", 600, 3, "faint", "Oh no. Not the queen."),
    beat("r-2", "brilliant", 4100, 2, "slow_clap", "Wait, that works?"),
    beat("r-3", "missed_win", 7600, 2, "screaming", "He just had mate!"),
    beat("r-4", "comeback", 11_100, 2, "shocked", "Never mind, he's back!"),
    beat("r-5", "promotion", 14_200, 1, "jealous", "Why not me?"),
    beat("r-6", "checkmate", 17_100, 3, "mic_drop", "Two pieces. Done."),
  ],
};

export const REEL_FRAMES = 600;
const BOARD: Box = { x: 136, y: 140, w: 800, h: 800 };
const STUDIO_BOX: Box = { x: 1000, y: 696, w: 824, h: 288 };

export const MascotReel: React.FC = () => {
  useFonts();
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { color, font, size } = tokens;
  const reactions = reactionsFor(REEL_SPEC.beats, fps, durationInFrames);
  const held = freezeAt(frame, reactions);
  const boardFrame = held ?? frame; // what a scene's board would show: it holds during the freeze
  const dotX = BOARD.x + 40 + ((boardFrame * 6) % (BOARD.w - 80));
  const label = { position: "absolute", fontFamily: font.mono, fontSize: size.label, color: color.muted } as const;
  return (
    <AbsoluteFill style={{ backgroundColor: color.bg }}>
      <div style={{ position: "absolute", left: BOARD.x, top: BOARD.y, width: BOARD.w, height: BOARD.h, backgroundColor: color.surface, border: `2px solid ${color.hairline}` }} />
      <div style={{ position: "absolute", left: dotX, top: BOARD.y + BOARD.h / 2, width: 32, height: 32, borderRadius: 16, backgroundColor: held === null ? color.text : color.blunder }} />
      <div style={{ ...label, left: BOARD.x + 24, top: BOARD.y + 24 }}>mock board{held !== null ? ": frozen" : ""}</div>
      <div style={{ ...label, left: STUDIO_BOX.x, top: STUDIO_BOX.y - 44 }}>mascot box (clip edge)</div>
      <div style={{ position: "absolute", left: STUDIO_BOX.x, top: STUDIO_BOX.y, width: STUDIO_BOX.w, height: STUDIO_BOX.h, border: `2px solid ${color.hairline}`, boxSizing: "border-box" }} />
      <MascotLayer spec={REEL_SPEC} box={STUDIO_BOX} height={200} />
    </AbsoluteFill>
  );
};
