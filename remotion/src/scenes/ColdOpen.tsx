import type { FC } from "react";
import { useMemo } from "react";
import type { VideoSpec } from "../spec/schema";
import { fontFor, useFonts } from "../theme/fonts";
import { studioLayout } from "../theme/layout";
import { tokens } from "../theme/tokens";
import { Enter } from "../ui/Enter";
import { coldOpenSpec } from "./helpers";
import { MascotSlot } from "./MascotSlot";
import { StudioBoard } from "./StudioBoard";
import type { SceneRange } from "./timeline";

const { hook, mascot } = studioLayout.boxes;

/** The game's biggest moment first: plies cold_open.ply_from..ply_to on the board, the hook line on the right. */
export const ColdOpen: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  useFonts();
  const cold = useMemo(() => coldOpenSpec(spec, range), [spec, range]);
  const hi = spec.language === "hi";
  return (
    <>
      <StudioBoard spec={cold} />
      <Enter atMs={range.startMs} style={{ position: "absolute", left: hook.x, top: hook.y, width: hook.w, height: hook.h }}>
        <div
          style={{
            fontFamily: fontFor(spec.language, "title"),
            fontWeight: 600,
            fontSize: hi ? 64 : tokens.size.title,
            lineHeight: hi ? 1.3 : 1.1,
            color: tokens.color.text,
            wordBreak: "keep-all",
          }}
        >
          {spec.cold_open.hook}
        </div>
      </Enter>
      <MascotSlot spec={spec} box={mascot} />
    </>
  );
};
