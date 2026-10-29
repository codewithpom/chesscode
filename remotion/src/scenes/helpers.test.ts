import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildPositions } from "../board/positions";
import { boardStateAt } from "../board/boardState";
import { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { clockFor, coldOpenSpec, currentPlyAt, moveLabel, resultText, yearOf } from "./helpers";

const spec = VideoSpec.parse(
  JSON.parse(readFileSync(resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"), "utf8")),
);
const FPS = 30;

describe("coldOpenSpec", () => {
  const range = { startMs: 0, endMs: 5400 };
  const cold = coldOpenSpec(spec, range);
  const positions = buildPositions(spec.game.pgn);
  const at = (ms: number) => boardStateAt(msToFrame(ms, FPS), FPS, cold.plies, positions);

  it("shows the position before ply_from first, with the earlier move already landed and no arrows", () => {
    const s = at(100);
    expect(s.ply).toBe(30);
    expect(s.arrows).toEqual([]);
    expect(s.pieces.map((p) => `${p.id}@${p.x},${p.y}`).sort()).toEqual(
      positions[30].pieces.map((p) => `${p.id}@${p.square.charCodeAt(0) - 97},${8 - Number(p.square[1])}`).sort(),
    );
  });

  it("plays ply_from..ply_to inside the range, in order, and never shows later plies", () => {
    const times = cold.plies.filter((p) => p.ply >= 31 && p.ply <= 33).map((p) => p.show_at_ms);
    expect(times).toEqual([...times].sort((a, b) => a - b));
    expect(times[0]).toBeGreaterThanOrEqual(0);
    expect(times[2] + 280).toBeLessThanOrEqual(5400);
    expect(at(5399).ply).toBe(33);
    expect(cold.plies.find((p) => p.ply === 34)).toBeUndefined(); // the fixture ends at ply 33
  });

  it("leaves the input untouched", () => {
    expect(spec.plies[30].show_at_ms).not.toBe(cold.plies[30].show_at_ms);
  });
});

describe("small helpers", () => {
  it("currentPlyAt", () => {
    expect(currentPlyAt(spec.plies, 0, FPS)).toBe(null);
    expect(currentPlyAt(spec.plies, msToFrame(spec.plies[4].show_at_ms, FPS), FPS)).toBe(5);
  });
  it("clockFor finds the latest clock of that side", () => {
    const plies = [
      { ply: 1, clock_ms: 600 },
      { ply: 2, clock_ms: 590 },
      { ply: 3, clock_ms: null },
      { ply: 4, clock_ms: 580 },
    ];
    expect(clockFor(plies, "white", 4)).toBe(600);
    expect(clockFor(plies, "black", 4)).toBe(580);
    expect(clockFor(plies, "black", 1)).toBe(null);
    expect(clockFor(spec.plies, "white", 20)).toBe(null); // fixture has no clock data
  });
  it("yearOf, resultText, moveLabel", () => {
    expect(yearOf("1858-11-02")).toBe("1858");
    expect(yearOf("1858.??.??")).toBe("1858");
    expect(yearOf("?")).toBe("");
    expect(resultText("1/2-1/2")).toBe("½–½");
    expect(moveLabel({ ply: 19, san: "Bxb5+" })).toBe("10. Bxb5+");
    expect(moveLabel({ ply: 20, san: "Qxb5" })).toBe("10... Qxb5");
  });
});
