import { describe, expect, it } from "vitest";
import { settledState } from "./boardState";
import { buildPositions } from "./positions";

// 1.e4 e5 2.Nf3 Nc6, plies only 300 ms apart: a "show_at_ms + 600" snapshot of ply 1 would already hold ply 3.
const positions = buildPositions("1. e4 e5 2. Nf3 Nc6 *");
const plies = positions.slice(1).map((s, i) => ({
  ply: i + 1,
  show_at_ms: i * 300,
  arrows: [{ from: s.move!.from, to: s.move!.to, color: "best" as const }],
  highlights: [{ square: s.move!.to, kind: "last_move" as const }],
}));
const squares = (ply: number) =>
  settledState(ply, plies, positions)
    .pieces.map((p) => `${p.id}@${p.x},${p.y}`)
    .sort();
const expected = (ply: number) => positions[ply].pieces.map((p) => `${p.id}@${p.square.charCodeAt(0) - 97},${8 - Number(p.square[1])}`).sort();

describe("settledState", () => {
  it("is the finished position after exactly that ply, however close the next plies are", () => {
    for (const ply of [0, 1, 2, 3, 4]) expect(squares(ply)).toEqual(expected(ply));
    expect(squares(1)).not.toEqual(expected(3));
  });

  it("carries that ply's own highlight and arrow, with every piece at rest", () => {
    const s = settledState(2, plies, positions);
    expect(s.highlights).toEqual([{ square: "e5", kind: "last_move" }]);
    expect(s.arrows).toEqual([{ from: "e7", to: "e5", color: "best" }]);
    expect(s.pieces.every((p) => p.opacity === 1 && p.scale === 1)).toBe(true);
    expect(settledState(2, plies, positions, false).arrows).toEqual([]);
    expect(settledState(0, plies, positions)).toMatchObject({ highlights: [], arrows: [] });
  });
});
