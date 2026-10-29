import type { PoseState } from "../poseState";
import { n, P, STROKE } from "./kit";

const Eye: React.FC<{ cx: number; side: "l" | "r"; s: PoseState }> = ({ cx, side, s }) => {
  const cy = 90;
  const rx = 18 * s.eyeScale;
  const ry = 24 * s.eyeScale;
  if (s.eyeOpen < 0.06) {
    return (
      <g id={`eye-${side}`}>
        <path d={`M${n(cx - rx)},${cy} Q${cx},${cy + 7} ${n(cx + rx)},${cy}`} fill="none" stroke={P.ink} strokeWidth={STROKE + 1} strokeLinecap="round" />
      </g>
    );
  }
  // Pupil shrinks as the eye widens (shock); PoseState has no separate pupil-size field.
  const pr = 8.5 * Math.min(1.2, Math.max(0.4, 1 - 2.5 * (s.eyeScale - 1))) * s.eyeScale;
  const px = cx + s.pupilX * (rx - pr - 2);
  const py = cy + s.pupilY * (ry - pr - 2);
  const lidH = 2 * ry * (1 - s.eyeOpen);
  const ly = cy - ry + lidH;
  const dy = ly - cy;
  const w = rx * Math.sqrt(Math.max(0, 1 - (dy / ry) ** 2));
  return (
    <g id={`eye-${side}`}>
      <ellipse cx={cx} cy={cy} rx={n(rx)} ry={n(ry)} fill={P.body} />
      <circle cx={n(px)} cy={n(py)} r={n(pr)} fill={P.ink} />
      <circle cx={n(px + pr * 0.35)} cy={n(py - pr * 0.4)} r={n(Math.max(1.6, pr * 0.28))} fill={P.body} />
      {lidH > 0.5 && (
        <>
          <path d={`M${n(cx - w)},${n(ly)} A${n(rx)} ${n(ry)} 0 ${dy > 0 ? 1 : 0} 1 ${n(cx + w)},${n(ly)} Z`} fill={P.body} />
          <line x1={n(cx - w)} y1={n(ly)} x2={n(cx + w)} y2={n(ly)} stroke={P.ink} strokeWidth={STROKE - 0.5} />
        </>
      )}
      <ellipse cx={cx} cy={cy} rx={n(rx)} ry={n(ry)} fill="none" stroke={P.ink} strokeWidth={STROKE - 0.5} />
    </g>
  );
};

export const Eyes: React.FC<{ s: PoseState }> = ({ s }) => (
  <>
    <Eye cx={96} side="l" s={s} />
    <Eye cx={144} side="r" s={s} />
  </>
);
