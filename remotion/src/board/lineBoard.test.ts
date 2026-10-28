import { Chess } from "chess.js";
import { describe, expect, it } from "vitest";
import { nextArrowIndex } from "./LineBoard";
import { lineStates } from "./positions";

const play = (fen: string, uci: string[]): string[] => {
  const g = new Chess(fen);
  return uci.map((u) => (g.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] }), g.fen()));
};

describe("lineStates", () => {
  it("matches chess.js FENs for a capture and a castle", () => {
    const start = new Chess().fen();
    const line = ["e2e4", "d7d5", "e4d5", "g8f6", "g1f3", "c8f5", "f1e2", "e7e6", "e1g1"]; // capture d5, kingside castle last
    const states = lineStates(start, line);
    expect(states.map((s) => s.fen).slice(1)).toEqual(play(start, line));
    expect(states[3].move!.captured).toBe("bP-d7");
    expect(states[9].move!.castleRook).toEqual({ id: "wR-h1", from: "h1", to: "f1" });
  });

  it("matches chess.js FENs for a promotion", () => {
    const fen = "8/P6k/8/8/8/8/7K/8 w - - 0 1";
    const line = ["a7a8q", "h7g7"];
    const states = lineStates(fen, line);
    expect(states.map((s) => s.fen).slice(1)).toEqual(play(fen, line));
    expect(states[1].move!.promotion).toBe("q");
    expect(states[1].pieces.find((p) => p.id === "wP-a7")!.type).toBe("q");
  });

  it("throws naming an illegal move", () => {
    expect(() => lineStates(new Chess().fen(), ["e2e4", "e2e4"])).toThrow(/illegal move e2e4 \(index 1\)/);
  });
});

describe("nextArrowIndex", () => {
  it("shows the next move's arrow before it starts and hides it while a piece slides", () => {
    expect(nextArrowIndex(-500, 1200, 3)).toBe(0);
    expect(nextArrowIndex(100, 1200, 3)).toBeNull(); // move 0 sliding
    expect(nextArrowIndex(300, 1200, 3)).toBe(1);
    expect(nextArrowIndex(2400 + 300, 1200, 3)).toBeNull(); // last move landed: nothing left
  });
});
