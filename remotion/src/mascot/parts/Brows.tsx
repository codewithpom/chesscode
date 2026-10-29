import type { PoseState } from "../poseState";
import { n, P, STROKE } from "./kit";

export const Brows: React.FC<{ s: PoseState }> = ({ s }) => {
  const y = 54 - Math.max(-1, Math.min(1, s.browY)) * 9; // capped so brows never hit the crown
  return (
    <>
      {(["l", "r"] as const).map((side) => {
        const x = side === "l" ? 96 : 144;
        const by = y - (side === "r" ? s.browRY * 8 : 0);
        const a = s.browAngle * 18 * (side === "l" ? 1 : -1);
        return (
          <line key={side} id={`brow-${side}`} x1={x - 10} y1={n(by)} x2={x + 10} y2={n(by)} stroke={P.ink} strokeWidth={STROKE + 1.5}
            strokeLinecap="round" transform={`rotate(${n(a)} ${x} ${n(by)})`} />
        );
      })}
    </>
  );
};
