import type { FC } from "react";
import { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { MascotLayer } from "../mascot";
import type { VideoSpec } from "../spec/schema";
import { frameToMs } from "../spec/time";
import { mascotBeats, mascotPlacement } from "./helpers";
import type { SceneRange } from "./timeline";

/**
 * Pyaada for the whole Studio video, mounted once (like the captions): the scene only picks his box and size. A
 * reaction that crosses a scene cut keeps its pose and bubble. Reads the video's own frame.
 */
export const StudioMascot: FC<{ spec: VideoSpec; ranges: SceneRange[] }> = ({ spec, ranges }) => {
  const { fps } = useVideoConfig();
  const where = mascotPlacement(ranges, frameToMs(useCurrentFrame(), fps));
  const withBeats = useMemo(() => ({ ...spec, beats: mascotBeats(spec, ranges) }), [spec, ranges]);
  if (!where) return null;
  return <MascotLayer spec={withBeats} box={where.box} height={where.height} />;
};
