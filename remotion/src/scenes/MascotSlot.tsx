import type { FC } from "react";
import { MascotLayer } from "../mascot";
import type { VideoSpec } from "../spec/schema";
import type { Box } from "../theme/layout";

/**
 * Pyaada and his speech bubble in `box` (the layer clips to it, except for a faint's own fall). `spec.beats` drive
 * the reactions; mount where the frame is the video's own.
 */
export const MascotSlot: FC<{ spec: VideoSpec; box: Box; height: number; bubbleFont?: number; maxBubbleH?: number }> = (props) => (
  <MascotLayer {...props} />
);
