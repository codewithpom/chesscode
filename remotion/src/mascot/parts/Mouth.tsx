import type { MouthId } from "../poseState";
import { P, STROKE } from "./kit";

const line = { stroke: P.ink, strokeWidth: STROKE, strokeLinecap: "round", strokeLinejoin: "round", fill: "none" } as const;
const cx = 120;
const cy = 126;

const SHAPES: Record<MouthId, React.ReactNode> = {
  smile: <path d={`M${cx - 11},${cy - 2} Q${cx},${cy + 8} ${cx + 11},${cy - 2}`} {...line} />,
  flat: <path d={`M${cx - 6},${cy + 1} L${cx + 10},${cy - 1}`} {...line} />,
  frown: <path d={`M${cx - 10},${cy + 4} Q${cx},${cy - 5} ${cx + 10},${cy + 4}`} {...line} />,
  smirk: <path d={`M${cx - 9},${cy + 1} Q${cx + 2},${cy + 5} ${cx + 12},${cy - 4}`} {...line} />,
  o: <ellipse cx={cx} cy={cy + 3} rx={9} ry={12} fill={P.ink} />,
  wide: <ellipse cx={cx} cy={cy + 6} rx={15} ry={19} fill={P.ink} />,
  open_talk: <ellipse cx={cx} cy={cy + 3} rx={10} ry={7} fill={P.ink} />,
};

export const Mouth: React.FC<{ mouth: MouthId }> = ({ mouth }) => <g id="mouth">{SHAPES[mouth]}</g>;
