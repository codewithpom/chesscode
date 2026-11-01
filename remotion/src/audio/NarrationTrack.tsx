import { Audio } from "@remotion/media";
import { Sequence, staticFile, useVideoConfig } from "remotion";
import type { NarrationSegment } from "../spec/schema";
import { msToFrame } from "../spec/time";

// One <Audio> per segment, inside a <Sequence> at its start_ms (spec section 5).
// Compensate for the 3 dB gain when mono narration is mixed into stereo.
export const NarrationTrack: React.FC<{ segments: NarrationSegment[] }> = ({ segments }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {segments.map((s) => (
        <Sequence key={s.segment_id} from={msToFrame(s.start_ms, fps)} durationInFrames={msToFrame(s.duration_ms, fps)}>
          <Audio src={staticFile(s.audio)} volume={Math.SQRT1_2} />
        </Sequence>
      ))}
    </>
  );
};
