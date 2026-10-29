import type { FC } from "react";
import { useMemo } from "react";
import type { VideoSpec } from "../spec/schema";
import { studioLayout } from "../theme/layout";
import { signOffBeats } from "./helpers";
import { MascotSlot } from "./MascotSlot";
import type { SceneRange } from "./timeline";

/**
 * Sign-off in the left third: Pyaada waves, then points toward the right two thirds, which are reserved for
 * YouTube end-screen elements and never drawn on. His lines are the two sign-off beats.
 */
export const Outro: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  const signOff = useMemo(() => ({ ...spec, beats: signOffBeats(spec, range) }), [spec, range]);
  return <MascotSlot spec={signOff} box={studioLayout.boxes.outroMascot} height={studioLayout.outroMascotHeight} />;
};
