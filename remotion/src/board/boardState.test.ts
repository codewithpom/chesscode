import { describe, expect, it } from "vitest";
import { msToFrame } from "../spec/time";
import { motion } from "../theme/motion";
import { boardStateAt, orient, type PlyInput } from "./boardState";
import { games } from "./fixtures/games";
import { buildPositions } from "./positions";

// fps 50 => 20 ms per frame, so 140/220/280 ms all land exactly on frames.
const FPS = 50;
const T0 = 1000; // first ply show_at_ms
const GAP = 2000;
const frameAt = (ply: number, elapsedMs: number): number =>
  msToFrame(T0 + (ply - 1) * GAP, FPS) + msToFrame(elapsedMs, FPS);

const setup = (name: string) => {
  const pgn = games.find((g) => g.name.includes(name))!.pgn;
  const positions = buildPositions(pgn);
  const plies: PlyInput[] = positions.slice(1).map((s, i) => ({
    ply: i + 1,
    show_at_ms: T0 + i * GAP,
    arrows: [{ from: s.move!.from, to: s.move!.to, color: "best" }],
    highlights: [
      { square: s.move!.from, kind: "last_move" },
      { square: s.move!.to, kind: "last_move" },
    ],
  }));
  return { positions, plies, at: (frame: number) => boardStateAt(frame, FPS, plies, positions) };
};
const piece = (s: ReturnType<typeof boardStateAt>, id: string) => s.pieces.find((p) => p.id === id);

describe("boardStateAt", () => {
  it("piece at rest before show_at", () => {
    const { at, positions } = setup("scholar");
    const s = at(frameAt(1, 0) - 1);
    expect(s.ply).toBe(0);
    expect(s.pieces).toHaveLength(positions[0].pieces.length);
    expect(piece(s, "wP-e2")).toMatchObject({ x: 4, y: 6, opacity: 1, scale: 1 });
    expect(s.highlights).toEqual([]);
    expect(s.arrows).toEqual([]);
  });

  it("midway at 140 ms is halfway with eased progress", () => {
    const { at } = setup("scholar");
    const p = piece(at(frameAt(1, 140)), "wP-e2")!;
    expect(p.x).toBe(4);
    expect(p.y).toBeCloseTo(6 - 2 * motion.enter(0.5), 10);
    expect(p.y).toBeLessThan(5); // decelerating curve is past the linear midpoint
    expect(piece(at(frameAt(1, 280)), "wP-e2")).toMatchObject({ x: 4, y: 4 });
  });

  it("captured piece opacity 0 at end", () => {
    const { at } = setup("scholar"); // ply 7: Qxf7#
    expect(piece(at(frameAt(7, 140)), "bP-f7")!.opacity).toBe(1);
    expect(piece(at(frameAt(7, 220)), "bP-f7")!.opacity).toBeCloseTo(0.5, 10);
    expect(piece(at(frameAt(7, 280)), "bP-f7")?.opacity ?? 0).toBe(0);
  });

  it("castling rook arrives with king", () => {
    const { at } = setup("ruy lopez"); // ply 9: O-O
    const mid = at(frameAt(9, 140));
    const k = piece(mid, "wK-e1")!;
    const r = piece(mid, "wR-h1")!;
    expect((k.x - 4) / 2).toBeCloseTo((7 - r.x) / 2, 10); // same progress
    expect(k.x).toBeGreaterThan(4);
    const end = at(frameAt(9, 280));
    expect(piece(end, "wK-e1")).toMatchObject({ x: 6, y: 7 });
    expect(piece(end, "wR-h1")).toMatchObject({ x: 5, y: 7 });
  });

  it("en passant pawn removed", () => {
    const { at } = setup("en passant by white"); // ply 5: exd6 e.p.
    const during = at(frameAt(5, 20));
    expect(piece(during, "bP-d7")).toMatchObject({ x: 3, y: 3, opacity: 1 }); // still on d5
    const end = at(frameAt(5, 280));
    expect(piece(end, "bP-d7")).toBeUndefined();
    expect(end.pieces.some((p) => p.x === 3 && p.y === 3)).toBe(false);
  });

  it("capture-promotion swaps at end", () => {
    const { at, positions } = setup("capture-promotion"); // ply 1: exd8=Q+
    const before = at(frameAt(1, 260));
    expect(piece(before, "wP-e7")).toMatchObject({ type: "p", scale: 1 });
    expect(piece(before, "bR-d8")!.opacity).toBeCloseTo(1 / 6, 10); // fading, still visible
    const swapped = at(frameAt(1, 280));
    expect(piece(swapped, "wP-e7")).toMatchObject({ type: "q", x: 3, y: 0, scale: 1 });
    expect(piece(swapped, "bR-d8")).toBeUndefined();
    const pop = piece(at(frameAt(1, 360)), "wP-e7")!; // middle of the 160 ms pop
    expect(pop.type).toBe("q");
    expect(pop.scale).toBeCloseTo(1.12, 10);
    const rest = at(frameAt(1, 440));
    expect(piece(rest, "wP-e7")).toMatchObject({ type: "q", scale: 1 });
    expect(rest.pieces).toHaveLength(positions[1].pieces.length);
  });

  it("highlights follow the move and arrows wait for it to land", () => {
    const { at } = setup("scholar");
    const mid = at(frameAt(1, 140));
    expect(mid.highlights).toHaveLength(2);
    expect(mid.arrows).toEqual([]);
    expect(at(frameAt(1, 280)).arrows).toHaveLength(1);
    expect(at(frameAt(2, 0)).arrows).toEqual([]);
  });

  it("is pure: same frame twice equals and random-order frames equal sequential", () => {
    const { at } = setup("capture-promotion");
    const frames = Array.from({ length: 80 }, (_, i) => i + 40);
    const sequential = frames.map(at);
    expect(at(60)).toEqual(at(60));
    let seed = 12345; // deterministic shuffle, no Math.random
    const order = [...frames];
    for (let i = order.length - 1; i > 0; i--) {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      const j = seed % (i + 1);
      [order[i], order[j]] = [order[j], order[i]];
    }
    for (const f of order) expect(at(f)).toEqual(sequential[f - 40]);
  });

  it("never more than 2 arrows", () => {
    const { positions } = setup("scholar");
    const three = (["best", "threat", "missed"] as const).map((color) => ({ from: "a1", to: "a2", color }));
    const plies: PlyInput[] = [{ ply: 1, show_at_ms: 0, arrows: three, highlights: [] }];
    expect(boardStateAt(msToFrame(1000, FPS), FPS, plies, positions).arrows.length).toBeLessThanOrEqual(2);
  });
});

describe("orient", () => {
  it("flips both axes for black at the bottom, identity for white", () => {
    expect(orient(1, 2, "white")).toEqual({ x: 1, y: 2 });
    expect(orient(1, 2, "black")).toEqual({ x: 6, y: 5 });
    expect(orient(0, 0, "black")).toEqual({ x: 7, y: 7 });
  });
});
