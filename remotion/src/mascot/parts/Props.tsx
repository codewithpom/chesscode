import type { PoseState } from "../poseState";
import { n, P, STROKE } from "./kit";

const ink = { stroke: P.ink, strokeWidth: STROKE, strokeLinejoin: "round" } as const;
const CROWN = "M0,32 L0,9 L13,19 L26,0 L39,19 L52,9 L52,32 Z";

export const Props: React.FC<{ s: PoseState }> = ({ s }) => {
  const { prop, propLift: lift, headTilt } = s;
  if (prop === "none") return null;
  const head = `rotate(${n(headTilt)} 120 140)`;
  return (
    <g id="prop">
      {prop === "crown" && s.arms === "hold" && (
        // Clutched to the chest between both hands.
        <path d={CROWN} fill={P.accent} {...ink} transform="translate(94,150) rotate(-8 26 16)" />
      )}
      {prop === "crown" && s.arms !== "hold" && (
        <g transform={head}>
          <path d={CROWN} fill={P.accent} {...ink} transform={`translate(${n(112 + lift * 0.3)},${n(8 - lift)}) rotate(${n(13 + lift * 0.8)})`} />
        </g>
      )}
      {prop === "party_hat" && (
        <g transform={head}>
          <g transform="translate(112,24) rotate(13 26 22)">
            <path d="M0,22 L26,-18 L52,22 Z" fill={P.accent} {...ink} />
            <circle cx={26} cy={-18} r={5} fill={P.body} {...ink} strokeWidth={STROKE - 1} />
          </g>
        </g>
      )}
      {prop === "binoculars" && (
        <g>
          <rect x={116} y={82} width={8} height={12} fill={P.ink} />
          {[96, 144].map((cx) => (
            <g key={cx}>
              <rect x={cx - 20} y={66} width={40} height={50} rx={12} fill={P.ink} {...ink} />
              <circle cx={cx} cy={91} r={12} fill={P.shade} stroke={P.body} strokeWidth={3} />
            </g>
          ))}
        </g>
      )}
      {prop === "watch" && (
        <g transform={`rotate(${n(s.armL)} 92 156)`}>
          <circle cx={90} cy={170} r={8} fill={P.body} {...ink} strokeWidth={STROKE - 1} />
          <path d="M90,170 L90,165 M90,170 L94,171" fill="none" stroke={P.ink} strokeWidth={2} strokeLinecap="round" />
        </g>
      )}
      {prop === "mic" && (
        // Origin = bottom of the handle; at lift 0 it sits in the raised hand, at -147 on the ground.
        <g transform={`translate(${n(204 + 18 * Math.min(1, Math.max(0, -lift / 147)))},${n(102 - lift)})`}>
          <rect x={-4} y={-26} width={8} height={26} rx={3} fill={P.shade} {...ink} strokeWidth={STROKE - 1} />
          <circle cx={0} cy={-34} r={10} fill={P.body} {...ink} />
        </g>
      )}
    </g>
  );
};
