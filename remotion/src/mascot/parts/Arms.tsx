import type { ArmsId, PoseState, PropId } from "../poseState";
import { n, P, STROKE } from "./kit";

type Pt = [number, number];
export type Limb = { points: [Pt, Pt, Pt]; handR: number };
export type ArmSet = { l?: Limb; r?: Limb };

const limb = (a: Pt, b: Pt, c: Pt, handR = 13): Limb => ({ points: [a, b, c], handR });

// Shoulder, elbow, hand per arm: two segments (spec section 7). Face, clap and up are the sheet's geometry.
export const armSet = (arms: ArmsId, prop: PropId): ArmSet => {
  switch (arms) {
    case "none": return {};
    case "face": return { r: limb([150, 156], [212, 150], [138, 90], 22) };
    case "clap": return { l: limb([92, 154], [56, 196], [106, 172]), r: limb([148, 154], [184, 196], [134, 172]) };
    case "up": return { r: limb([150, 156], [198, 140], [204, 92]) };
    case "chin": return { r: limb([150, 156], [190, 178], [130, 148]) };
    case "wrist": return { l: limb([92, 156], [58, 178], [108, 168]) };
    case "point": return { r: limb([150, 156], [188, 132], [224, 112]) };
    case "hold":
      return prop === "binoculars"
        ? { l: limb([92, 156], [58, 150], [84, 112]), r: limb([148, 156], [182, 150], [156, 112]) }
        : { l: limb([92, 156], [66, 178], [94, 170]), r: limb([148, 156], [174, 178], [146, 170]) };
  }
};

const Hand: React.FC<{ x: number; y: number; r: number }> = ({ x, y, r }) => {
  const sk = { fill: P.body, stroke: P.ink, strokeWidth: STROKE - 0.5 } as const;
  if (r < 20) {
    return (
      <>
        <circle cx={x} cy={n(y - r * 0.75)} r={n(r * 0.42)} {...sk} />
        <ellipse cx={x} cy={y} rx={n(r * 0.8)} ry={r} {...sk} />
      </>
    );
  }
  // Open palm over the face: a wide mitten with finger creases, so it never reads as a monocle.
  return (
    <>
      <ellipse cx={x} cy={y} rx={n(r * 1.3)} ry={n(r * 0.85)} transform={`rotate(-12 ${x} ${y})`} {...sk} />
      {[-6, 1, 8].map((dy) => (
        <line key={dy} x1={n(x - r * 0.95)} y1={y + dy} x2={n(x - r * 0.35)} y2={y + dy} stroke={P.ink} strokeWidth={STROKE - 1} strokeLinecap="round" />
      ))}
    </>
  );
};

const Arm: React.FC<{ side: "l" | "r"; limb: Limb; swing: number }> = ({ side, limb: l, swing }) => {
  const [[x0, y0], [x1, y1], [x2, y2]] = l.points;
  const d = `M${x0},${y0} L${x1},${y1} L${x2},${y2}`;
  return (
    <g id={`arm-${side}`} transform={`rotate(${n(swing)} ${x0} ${y0})`}>
      <path d={d} fill="none" stroke={P.ink} strokeWidth={STROKE + 11} strokeLinecap="round" strokeLinejoin="round" />
      <path d={d} fill="none" stroke={P.body} strokeWidth={STROKE + 4} strokeLinecap="round" strokeLinejoin="round" />
      <Hand x={x2} y={y2} r={l.handR} />
    </g>
  );
};

export const Arms: React.FC<{ s: PoseState }> = ({ s }) => {
  const set = armSet(s.arms, s.prop);
  return (
    <>
      {set.l && <Arm side="l" limb={set.l} swing={s.armL} />}
      {set.r && <Arm side="r" limb={set.r} swing={s.armR} />}
    </>
  );
};
