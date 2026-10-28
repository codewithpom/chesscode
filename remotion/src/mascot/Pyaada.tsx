import type { PoseState } from "./poseState";
import { scaleOf } from "./poseState";
import { Arms } from "./parts/Arms";
import { Base } from "./parts/Base";
import { Body, Head } from "./parts/Body";
import { Brows } from "./parts/Brows";
import { Eyes } from "./parts/Eyes";
import { n, P, STROKE } from "./parts/kit";
import { Mouth } from "./parts/Mouth";
import { Props } from "./parts/Props";

/** Rig box (design/mascot/build_sheets.py local box): 240 x 260, ground at y = 249. */
export const RIG = { w: 240, h: 260, groundX: 120, groundY: 249 } as const;

const Sweat: React.FC<{ t: number }> = ({ t }) => {
  const k = 1.5 * Math.min(1, t * 3);
  return (
    <g transform={`translate(166,${n(42 + 30 * t)})`}>
      <path
        d={`M0,0 C${n(9 * k)},${n(12 * k)} ${n(10 * k)},${n(20 * k)} 0,${n(22 * k)} C${n(-10 * k)},${n(20 * k)} ${n(-9 * k)},${n(12 * k)} 0,0 Z`}
        fill={P.body} stroke={P.ink} strokeWidth={STROKE - 1} strokeLinejoin="round"
      />
    </g>
  );
};

/** The rig, drawn from a PoseState. Layers: base, body, head (+ eyes, brows, mouth), arms, prop. */
export const Pyaada: React.FC<{ state: PoseState; height: number }> = ({ state: s, height }) => {
  const { x, y } = scaleOf(s.squash);
  const body =
    `translate(${n(s.offsetX)} ${n(s.offsetY)}) rotate(${n(s.lean)} ${RIG.groundX} ${RIG.groundY}) ` +
    `translate(${RIG.groundX} ${RIG.groundY}) scale(${n(x)} ${n(y)}) translate(${-RIG.groundX} ${-RIG.groundY})`;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${RIG.w} ${RIG.h}`}
      width={n((height * RIG.w) / RIG.h)} height={height} style={{ overflow: "visible", display: "block" }}
    >
      <g transform={body}>
        <Base />
        <Body />
        <g id="head-group" transform={`rotate(${n(s.headTilt)} 120 140)`}>
          <Head />
          <Eyes s={s} />
          <Brows s={s} />
          <Mouth mouth={s.mouth} />
          {s.sweat > 0 && <Sweat t={s.sweat} />}
        </g>
        <Arms s={s} />
        <Props s={s} />
      </g>
    </svg>
  );
};
