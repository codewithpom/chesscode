import { Audio } from "@remotion/media";
import { Sequence, staticFile, useVideoConfig } from "remotion";
import type { NarrationSegment } from "../spec/schema";
import { msToFrame } from "../spec/time";

// One <Audio> per segment, inside a <Sequence> at its start_ms (spec section 5).
export const NarrationTrack: React.FC<{ segments: NarrationSegment[] }> = ({ segments }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {segments.map((s) => (
        <Sequence key={s.segment_id} from={msToFrame(s.start_ms, fps)} durationInFrames={msToFrame(s.duration_ms, fps)}>
          <Audio src={staticFile(s.audio)} />
        </Sequence>
      ))}
    </>
  );
};
