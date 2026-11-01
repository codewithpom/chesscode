import { describe, expect, it } from "vitest";
import { blendStates, loopProgress } from "./loopBlend";
import { boardStateAt } from "./boardState";
import { buildPositions } from "./positions";

const FPS = 30;
const pgn = "1. e4 d5 2. exd5 *";
const positions = buildPositions(pgn);
const plies = positions.slice(1).map((s, i) => ({ ply: i + 1, show_at_ms: i * 1000, arrows: [], highlights: [{ square: s.move!.to, kind: "last_move" as const }] }));
const start = boardStateAt(0, FPS, [], positions);
const end = boardStateAt(120, FPS, plies, positions); // after exd5: the black d-pawn is gone

const at = (s: ReturnType<typeof boardStateAt>) => s.pieces.map((p) => `${p.id}@${p.x},${p.y}:${p.opacity}`).sort();

describe("loopProgress", () => {
  it("is 0 until the last 10 frames and exactly 1 on the last frame", () => {
    expect(loopProgress(0, 100)).toBe(0);
    expect(loopProgress(90, 100)).toBe(0);
    expect(loopProgress(99, 100)).toBe(1);
    expect(loopProgress(95, 100)).toBeGreaterThan(0);
    expect(loopProgress(95, 100)).toBeLessThan(1);
  });
});

describe("blendStates", () => {
  it("t=0 is the end position and t=1 is the start position, piece for piece", () => {
    expect(at(blendStates(end, start, 0))).toEqual(at({ ...end, pieces: end.pieces }).concat([`bP-d7@3,1:0`]).sort());
    expect(at(blendStates(end, start, 1))).toEqual(at(start));
  });
  it("the captured piece fades in and arrows are dropped", () => {
    const mid = blendStates(end, start, 0.6);
    const d7 = mid.pieces.find((p) => p.id === "bP-d7")!;
    expect(d7.opacity).toBeGreaterThan(0);
    expect(d7.opacity).toBeLessThan(1);
    expect(mid.arrows).toEqual([]);
  });
  it("uses the opening highlights once past halfway", () => {
    expect(blendStates(end, start, 0.2).highlights).toEqual(end.highlights);
    expect(blendStates(end, start, 0.9).highlights).toEqual(start.highlights);
  });
});
