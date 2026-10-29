import type { FC } from "react";
import type { VideoSpec } from "../spec/schema";
import { studioLayout } from "../theme/layout";
import { MascotSlot } from "./MascotSlot";

/**
 * Mascot sign-off in the left third. The right two thirds (x >= 640) are reserved for YouTube end-screen
 * elements and nothing is ever drawn there.
 */
export const Outro: FC<{ spec: VideoSpec }> = ({ spec }) => <MascotSlot spec={spec} box={studioLayout.boxes.outroMascot} />;
