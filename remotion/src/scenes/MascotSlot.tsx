import type { FC } from "react";
import type { Box } from "../theme/layout";
import type { VideoSpec } from "../spec/schema";

/**
 * Where the mascot goes. Task 7 (after M4 merges) puts `<MascotLayer spec box height />` here; until then the
 * box stays reserved in the layout and nothing is drawn, so no placeholder reaches a render.
 */
export const MascotSlot: FC<{ spec: VideoSpec; box: Box }> = () => null;
