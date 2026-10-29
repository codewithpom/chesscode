import type { PoseState } from "../poseState";
import { n, P, STROKE } from "./kit";

const ink = { stroke: P.ink, strokeWidth: STROKE, strokeLinejoin: "round" } as const;
const CROWN = "M0,32 L0,9 L13,19 L26,0 L39,19 L52,9 L52,32 Z";
const headTilt = (s: PoseState) => `rotate(${n(s.headTilt)} 120 140)`;

/** The paper crown, worn on the head in every pose except the party hat swap; clutched to the chest when jealous. */
export const Crown: React.FC<{ s: PoseState }> = ({ s }) => {
  if (s.prop === "party_hat") return null;
  if (s.prop === "crown" && s.arms === "hold") {
    return <path id="crown" d={CROWN} fill={P.accent} {...ink} transform="translate(94,150) rotate(-8 26 16)" />;
  }
  const lift = s.prop === "crown" ? Math.max(0, s.propLift) : 0; // propLift belongs to the hand prop otherwise
  return (
    <g id="crown" transform={headTilt(s)}>
      <path d={CROWN} fill={P.accent} {...ink} transform={`translate(${n(112 + lift * 0.3)},${n(8 - lift)}) rotate(${n(13 + lift * 0.8)})`} />
    </g>
  );
};

/** Party hat, binoculars, watch and mic. Renders nothing (no prop group) for crown and none. */
export const Props: React.FC<{ s: PoseState }> = ({ s }) => {
  const { prop, propLift: lift } = s;
  if (prop === "none" || prop === "crown") return null;
  return (
    <g id="prop">
      {prop === "party_hat" && (
        <g transform={headTilt(s)}>
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
          <circle cx={86} cy={172} r={13} fill={P.body} {...ink} />
          {[0, 90, 180, 270].map((a) => (
            <line key={a} x1={86} y1={162.5} x2={86} y2={165.5} stroke={P.ink} strokeWidth={2} strokeLinecap="round" transform={`rotate(${a} 86 172)`} />
          ))}
          <path d="M86,172 L86,166 M86,172 L91,174" fill="none" stroke={P.ink} strokeWidth={2.5} strokeLinecap="round" />
        </g>
      )}
      {prop === "mic" && (
        // Origin = the raised hand's tip; at lift 0 the handle is in the hand, at -102 it stands on the rim of the base.
        <g transform={`translate(${n(204 - 8 * Math.min(1, Math.max(0, -lift / 102)))},${n(92 - lift)})`}>
          <rect x={-5} y={-10} width={10} height={44} rx={4} fill={P.ink} {...ink} strokeWidth={STROKE - 1} />
          <circle cx={0} cy={-26} r={16} fill={P.shade} {...ink} />
          <path d="M-9,-30 L9,-30 M-9,-22 L9,-22" stroke={P.ink} strokeWidth={2.5} strokeLinecap="round" />
        </g>
      )}
    </g>
  );
};
