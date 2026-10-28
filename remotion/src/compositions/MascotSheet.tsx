// Review still: all 17 poses in a labelled grid (docs/SPEC.md section 7, creation workflow step 3).
import { AbsoluteFill } from "remotion";
import { Pyaada } from "../mascot/Pyaada";
import { POSES } from "../mascot/poses";
import { useFonts } from "../theme/fonts";
import { tokens } from "../theme/tokens";

const COLS = 6;
const CELL_W = 320;
const CELL_H = 340;
const HEIGHT = 230;

export const MascotSheet: React.FC = () => {
  useFonts();
  const { color, font, size } = tokens;
  return (
    <AbsoluteFill style={{ backgroundColor: color.bg }}>
      {(Object.keys(POSES) as (keyof typeof POSES)[]).map((name, i) => {
        // Faint is shown in place (shifted left) so the pose itself is reviewable; in video it leaves the box.
        const state = name === "faint" ? { ...POSES.faint, offsetX: -105, offsetY: -45 } : POSES[name];
        const x = (i % COLS) * CELL_W;
        const y = Math.floor(i / COLS) * CELL_H;
        return (
          <div key={name} style={{ position: "absolute", left: x + 16, top: y + 16, width: CELL_W - 32, height: CELL_H - 32, backgroundColor: color.surface, borderRadius: 16, overflow: "hidden" }}>
            <div style={{ position: "absolute", left: 0, right: 0, top: 24, display: "flex", justifyContent: "center" }}>
              <Pyaada state={state} height={HEIGHT} />
            </div>
            <div style={{ position: "absolute", left: 0, right: 0, bottom: 14, textAlign: "center", fontFamily: font.mono, fontSize: size.label, color: color.text }}>
              {name}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
