import { Audio } from "@remotion/media";
import { useEffect, useState } from "react";
import type { FC } from "react";
import { staticFile, useDelayRender, useVideoConfig } from "remotion";
import type { VideoSpec } from "../spec/schema";
import { frameToMs } from "../spec/time";
import { musicVolume } from "./musicVolume";

/** A track that is not a real file: silent bed, no error. (The pipeline writes its placeholder as a real silent MP3.) */
export const hasTrack = (music: VideoSpec["music"]): boolean => music.volume > 0 && !/placeholder|^none$/i.test(music.track);

/**
 * Music bed from the spec folder, looped, ducked under narration with 200 ms ramps. Mount at the video's own
 * frame 0. A track that cannot be fetched from the public dir renders silence instead of failing the render.
 */
export const MusicBed: FC<{ music: VideoSpec["music"]; narration: VideoSpec["narration"] }> = ({ music, narration }) => {
  const { fps } = useVideoConfig();
  const { delayRender, continueRender } = useDelayRender();
  const wanted = hasTrack(music);
  const [found, setFound] = useState<boolean | null>(wanted ? null : false);

  useEffect(() => {
    if (!wanted) return;
    const handle = delayRender(`Checking music track ${music.track}`);
    fetch(staticFile(music.track), { method: "HEAD" })
      .then((r) => setFound(r.ok))
      .catch(() => setFound(false))
      .finally(() => continueRender(handle));
  }, [wanted, music.track, delayRender, continueRender]);

  if (!found) return null;
  return <Audio src={staticFile(music.track)} loop volume={(frame) => musicVolume(frameToMs(frame, fps), narration, music)} />;
};
