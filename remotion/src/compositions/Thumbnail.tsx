// 1280 x 720 still (docs/SPEC.md section 6): the critical position cropped to its 4 x 4 window with the
// decisive arrow, the mascot large on the other side (box reserved, empty until M4 lands), at most 4 words.
//   npx remotion still Thumbnail out.png --props=<video_spec.json>
import type { FC } from "react";
import { AbsoluteFill, CalculateMetadataFunction } from "remotion";
import { Arrows } from "../board/Arrows";
import { orient, settledState, squareXY } from "../board/boardState";
import { Highlights } from "../board/Highlights";
import { Piece } from "../board/Piece";
import { buildPositions } from "../board/positions";
import { Square } from "../board/Square";
import { Pyaada, POSES } from "../mascot";
import { mascotWidth } from "../mascot/layerLayout";
import type { PoseState } from "../mascot/poseState";
import type { VideoSpec } from "../spec/schema";
import { boardThemes } from "../theme/boardThemes";
import { fontFor, useFonts } from "../theme/fonts";
import type { Box } from "../theme/layout";
import { tokens } from "../theme/tokens";

export const THUMB = { width: 1280, height: 720 } as const;
const TEXT: Box = { x: 64, y: 40, w: 1152, h: 144 };
const BOARD: Box = { x: 736, y: 208, w: 480, h: 480 };
const MASCOT: Box = { x: 64, y: 208, w: 640, h: 480 };
const MASCOT_HEIGHT = 480;

/** The pose as a still: faint's pose is the "fallen out of frame" end of an animation, so it is lying down in place instead. */
const stillPose = (pose: VideoSpec["thumbnail"]["pose"]): { state: PoseState; height: number } =>
  pose === "faint"
    ? { state: { ...POSES.faint, offsetX: 0, offsetY: 0 }, height: 340 }
    : { state: POSES[pose], height: MASCOT_HEIGHT };

export const calculateThumbnailMetadata: CalculateMetadataFunction<VideoSpec> = () => ({
  width: THUMB.width,
  height: THUMB.height,
  durationInFrames: 1,
  fps: 30,
});

/** The 4 x 4 window's 16 squares in the order they are drawn: left to right, top to bottom, as the board is oriented. `origin` is its lower-left square from White's view. */
export const cropWindow = (origin: string, orientation: "white" | "black"): string[] => {
  if (!/^[a-e][1-5]$/.test(origin)) throw new Error(`crop origin ${origin} must be a1..e5`);
  const f0 = origin.charCodeAt(0) - 97;
  const r0 = Number(origin[1]);
  const files = [0, 1, 2, 3].map((i) => f0 + i);
  const ranks = [3, 2, 1, 0].map((i) => r0 + i); // top row first, White's view
  const out: string[] = [];
  for (const r of ranks) for (const f of files) out.push(String.fromCharCode(97 + f) + r);
  return orientation === "white" ? out : out.reverse(); // Black at the bottom turns the window 180 degrees
};

/** SVG viewBox of the window in oriented board units. */
export const cropViewBox = (origin: string, orientation: "white" | "black"): string => {
  const pts = cropWindow(origin, orientation).map((sq) => {
    const { x, y } = squareXY(sq);
    return orient(x, y, orientation);
  });
  return `${Math.min(...pts.map((p) => p.x))} ${Math.min(...pts.map((p) => p.y))} 4 4`;
};

/** Words per line fit: one line, as large as the box allows, never below 72 px. */
const fitSize = (text: string, width: number, height: number): number =>
  Math.max(72, Math.min(height - 16, Math.floor(width / (Math.max(1, text.length) * 0.5))));

export const Thumbnail: FC<VideoSpec> = (spec) => {
  useFonts();
  const { text, ply: plyNo, crop_origin, pose } = spec.thumbnail;
  const mascot = stillPose(pose);
  const { orientation, theme } = spec.board;
  const palette = boardThemes[theme];
  const ply = spec.plies[plyNo - 1];
  const state = settledState(plyNo, spec.plies, buildPositions(spec.game.pgn));
  const arrow = ply.arrows[0] ?? { from: ply.uci.slice(0, 2), to: ply.uci.slice(2, 4), color: "best" as const };
  return (
    <AbsoluteFill style={{ backgroundColor: tokens.color.bg }}>
      <div
        style={{
          position: "absolute",
          left: TEXT.x,
          top: TEXT.y,
          width: TEXT.w,
          height: TEXT.h,
          display: "flex",
          alignItems: "center",
          fontFamily: fontFor(spec.language, "title"),
          fontWeight: 600,
          fontSize: fitSize(text, TEXT.w, TEXT.h),
          lineHeight: spec.language === "hi" ? 1.3 : 1.05,
          color: tokens.color.text,
          whiteSpace: "nowrap",
        }}
      >
        {text}
      </div>
      <div
        style={{
          position: "absolute",
          left: MASCOT.x + (pose === "faint" ? 60 : (MASCOT.w - mascotWidth(mascot.height)) / 2),
          top: MASCOT.y + MASCOT.h - mascot.height,
        }}
      >
        <Pyaada state={mascot.state} height={mascot.height} />
      </div>
      <svg
        style={{ position: "absolute", left: BOARD.x, top: BOARD.y, display: "block" }}
        width={BOARD.w}
        height={BOARD.h}
        viewBox={cropViewBox(crop_origin, orientation)}
      >
        {Array.from({ length: 64 }, (_, i) => {
          const x = i % 8;
          const y = Math.floor(i / 8);
          return <Square key={i} x={x} y={y} fill={(x + y) % 2 === 0 ? palette.light : palette.dark} />;
        })}
        <Highlights highlights={state.highlights} theme={theme} orientation={orientation} />
        {state.pieces.map((p) => {
          const o = orient(p.x, p.y, orientation);
          return <Piece key={p.id} type={p.type} color={p.color} x={o.x} y={o.y} opacity={p.opacity} scale={p.scale} />;
        })}
        <Arrows arrows={[arrow]} orientation={orientation} />
      </svg>
    </AbsoluteFill>
  );
};
