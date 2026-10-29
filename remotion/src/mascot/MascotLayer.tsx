import { useMemo } from "react";
import { AbsoluteFill, Sequence, random, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import { Circle, Rect, Triangle } from "@remotion/shapes";
import blip1 from "../assets/sfx/blip_1.mp3";
import blip2 from "../assets/sfx/blip_2.mp3";
import blip3 from "../assets/sfx/blip_3.mp3";
import blip4 from "../assets/sfx/blip_4.mp3";
import blip5 from "../assets/sfx/blip_5.mp3";
import blip6 from "../assets/sfx/blip_6.mp3";
import type { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import type { Box } from "../theme/layout";
import { layerRects } from "./layerLayout";
import { P } from "./parts/kit";
import { Pyaada } from "./Pyaada";
import { phaseAt, poseAt, reactionsFor, type Phase } from "./react";
import { blipFrames, SpeechBubble, typingEnd } from "./speech";

const BLIPS = [blip1, blip2, blip3, blip4, blip5, blip6];
const BLIP_FRAMES_MS = 90;
const CONFETTI = 28;
const CONFETTI_COLORS = [P.accent, P.body, P.shade];

const Confetti: React.FC<{ phase: Phase; box: Box; frame: number }> = ({ phase, box, frame }) => {
  const t = frame - phase.start;
  return (
    <>
      {Array.from({ length: CONFETTI }, (_, i) => {
        const k = (s: string) => random(`${phase.beatId}-confetti-${i}-${s}`);
        const age = t - Math.floor(k("delay") * 30);
        if (age < 0) return null;
        const size = 10 + k("size") * 8;
        const x = box.x + k("x") * box.w;
        const y = box.y - 20 + age * (4 + k("speed") * 4);
        const fill = CONFETTI_COLORS[Math.floor(k("color") * CONFETTI_COLORS.length)];
        const style = { position: "absolute", left: x, top: y, transform: `rotate(${k("rot") * 360 + age * (k("spin") * 12 - 6)}deg)` } as const;
        const shape = Math.floor(k("shape") * 3);
        return (
          <div key={i} style={style}>
            {shape === 0 ? <Rect width={size} height={size * 0.6} fill={fill} /> : shape === 1 ? <Circle radius={size / 2} fill={fill} /> : <Triangle length={size} direction="up" fill={fill} />}
          </div>
        );
      })}
    </>
  );
};

/** Pyaada, bottom-right in `box`, with the bubble for the active reaction and blip audio. Nothing is drawn outside `box`. */
export const MascotLayer: React.FC<{ spec: VideoSpec; box: Box; height: number }> = ({ spec, box, height }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height: frameH } = useVideoConfig();
  const reactions = useMemo(() => reactionsFor(spec.beats, fps, durationInFrames), [spec.beats, fps, durationInFrames]);
  const state = poseAt(frame, reactions, fps, spec.video_id);
  const { mascot, bubble } = layerRects(box, height);
  const active = reactions.find((r) => frame >= r.bubbleFrom && frame < r.bubbleTo);
  const talking = active !== undefined && frame < typingEnd(active.beat.mascot.line, active.bubbleFrom, fps, active.bubbleTo);
  // Mouth flaps every 3 frames while the bubble types.
  const flap = talking && Math.floor((frame - active.bubbleFrom) / 3) % 2 === 0;
  const phase = phaseAt(frame, reactions, fps);
  const party = phase?.pose === "party" ? phase : null;
  return (
    <AbsoluteFill style={{ clipPath: `inset(${box.y}px ${width - box.x - box.w}px ${frameH - box.y - box.h}px ${box.x}px)` }}>
      {party && <Confetti phase={party} box={box} frame={frame} />}
      <div style={{ position: "absolute", left: mascot.x, top: mascot.y }}>
        <Pyaada state={flap ? { ...state, mouth: "open_talk" } : state} height={height} />
      </div>
      {active && (
        <SpeechBubble line={active.beat.mascot.line} from={active.bubbleFrom} to={active.bubbleTo} box={bubble} language={spec.language} />
      )}
      {reactions.flatMap((r) =>
        blipFrames(r.beat.mascot.line, r.bubbleFrom, fps, `${spec.video_id}-${r.beat.beat_id}`, r.bubbleTo)
          .filter((b) => b.frame < Math.min(r.bubbleTo, durationInFrames))
          .map((b) => (
            <Sequence key={`${r.beat.beat_id}-${b.frame}`} from={b.frame} durationInFrames={msToFrame(BLIP_FRAMES_MS, fps) + 1} layout="none">
              <Audio src={BLIPS[b.sample - 1]} />
            </Sequence>
          )),
      )}
    </AbsoluteFill>
  );
};
