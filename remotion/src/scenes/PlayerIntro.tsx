import type { FC } from "react";
import type { VideoSpec } from "../spec/schema";
import { useFonts } from "../theme/fonts";
import { Enter, enterAt } from "../ui/Enter";
import { PlayerCard } from "../ui/PlayerCard";
import type { SceneRange } from "./timeline";

/** Two player cards with their one fact each, White then Black, entering one after the other. */
export const PlayerIntro: FC<{ spec: VideoSpec; range: SceneRange }> = ({ spec, range }) => {
  useFonts();
  return (
    <div style={{ position: "absolute", left: 96, top: 0, width: 1728, height: 1080, display: "flex", alignItems: "center", gap: 48 }}>
      {(["white", "black"] as const).map((side, i) => (
        <Enter key={side} atMs={enterAt(range.startMs, i)} style={{ flex: 1, minWidth: 0 }}>
          <PlayerCard player={spec.game[side]} side={side} lang={spec.language} fact size={40} />
        </Enter>
      ))}
    </div>
  );
};
