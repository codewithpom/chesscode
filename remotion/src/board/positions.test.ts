import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { Chess } from "chess.js";
import { describe, expect, it } from "vitest";
import { VideoSpec } from "../spec/schema";
import { games } from "./fixtures/games";
import { buildPositions, type PlyState } from "./positions";

// FEN piece-placement field rebuilt from the piece list, to check pieces independently of chess.js.
const fenPlacement = (s: PlyState): string => {
  const map = new Map(s.pieces.map((p) => [p.square, p]));
  const rows: string[] = [];
  for (let r = 8; r >= 1; r--) {
    let row = "";
    let empty = 0;
    for (let f = 0; f < 8; f++) {
      const p = map.get(String.fromCharCode(97 + f) + r);
      if (!p) empty++;
      else {
        row += (empty ? String(empty) : "") + (p.color === "w" ? p.type.toUpperCase() : p.type);
        empty = 0;
      }
    }
    rows.push(row + (empty ? String(empty) : ""));
  }
  return rows.join("/");
};

const all = games.map((g) => ({ ...g, states: buildPositions(g.pgn) }));
const moves = all.flatMap((g) => g.states.filter((s) => s.move));

describe("buildPositions", () => {
  it("there are 20 fixture games", () => expect(games).toHaveLength(20));

  it("FEN and piece list match chess.js for every ply of 20 fixture games", () => {
    for (const g of all) {
      const chess = new Chess();
      chess.loadPgn(g.pgn);
      const hist = chess.history({ verbose: true });
      expect(g.states).toHaveLength(hist.length + 1);
      expect(g.states[0].move).toBeNull();
      hist.forEach((m, i) => {
        expect(g.states[i + 1].fen, `${g.name} ply ${i + 1}`).toBe(m.after);
        expect(fenPlacement(g.states[i + 1]), `${g.name} ply ${i + 1}`).toBe(m.after.split(" ")[0]);
        expect(g.states[i + 1].move?.from).toBe(m.from);
        expect(g.states[i + 1].move?.to).toBe(m.to);
      });
    }
  });

  it("fixture spec fen_after matches", () => {
    const raw = readFileSync(
      resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"),
      "utf8",
    );
    const spec = VideoSpec.parse(JSON.parse(raw));
    const states = buildPositions(spec.game.pgn);
    expect(states).toHaveLength(spec.plies.length + 1);
    spec.plies.forEach((p, i) => expect(states[i + 1].fen).toBe(p.fen_after));
  });

  it("fixtures cover every special move", () => {
    const f = {
      castleK: { w: false, b: false },
      castleQ: { w: false, b: false },
      ep: false,
      promoQ: false,
      promoN: false,
      capPromoCheck: false,
    };
    for (const s of moves) {
      const m = s.move!;
      const color = s.pieces.find((p) => p.square === m.to)!.color;
      if (m.castleRook) (m.to[0] === "g" ? f.castleK : f.castleQ)[color] = true;
      if (m.enPassantSquare) f.ep = true;
      if (m.promotion === "q") f.promoQ = true;
      if (m.promotion === "n") f.promoN = true;
      if (m.promotion && m.captured && new Chess(s.fen).inCheck()) f.capPromoCheck = true;
    }
    expect(f).toEqual({
      castleK: { w: true, b: true },
      castleQ: { w: true, b: true },
      ep: true,
      promoQ: true,
      promoN: true,
      capPromoCheck: true,
    });
  });

  it("castling moves king and rook ids", () => {
    const st = moves.find((s) => s.move!.castleRook && s.move!.to === "g1")!;
    expect(st.move!.from).toBe("e1");
    expect(st.move!.castleRook).toEqual({ id: "wR-h1", from: "h1", to: "f1" });
    expect(st.pieces.find((p) => p.id === "wK-e1")!.square).toBe("g1");
    expect(st.pieces.find((p) => p.id === "wR-h1")!.square).toBe("f1");
    const q = moves.find((s) => s.move!.castleRook && s.move!.to === "c8")!;
    expect(q.move!.castleRook).toEqual({ id: "bR-a8", from: "a8", to: "d8" });
  });

  it("en passant captures the pawn on the correct square", () => {
    const g = all.find((x) => x.name === "en passant by white")!;
    const i = g.states.findIndex((s) => s.move?.enPassantSquare);
    const m = g.states[i].move!;
    expect(m.from).toBe("e5");
    expect(m.to).toBe("d6");
    expect(m.enPassantSquare).toBe("d5");
    expect(m.captured).toBe("bP-d7");
    expect(g.states[i - 1].pieces.some((p) => p.id === "bP-d7" && p.square === "d5")).toBe(true);
    expect(g.states[i].pieces.some((p) => p.id === "bP-d7")).toBe(false);
    const b = all.find((x) => x.name === "en passant by black")!;
    const j = b.states.findIndex((s) => s.move?.enPassantSquare);
    expect(b.states[j].move!.enPassantSquare).toBe("e4");
    expect(b.states[j].move!.captured).toBe("wP-e2");
  });

  it("promotion keeps the pawn id and sets promotion", () => {
    const g = all.find((x) => x.name === "white promotes to queen with check")!;
    const pawnBefore = g.states[0].pieces.find((p) => p.type === "p")!;
    expect(g.states[1].move!.promotion).toBe("q");
    expect(g.states[1].pieces.find((p) => p.id === pawnBefore.id)).toMatchObject({
      type: "q",
      square: "a8",
      color: "w",
    });
    const n = all.find((x) => x.name.includes("underpromotes"))!;
    expect(n.states[1].move!.promotion).toBe("n");
    expect(n.states[1].pieces.find((p) => p.square === "f8")!.type).toBe("n");
  });

  it("capture-promotion records the captured piece and the move", () => {
    const g = all.find((x) => x.name.includes("capture-promotion"))!;
    expect(g.states[1].move).toMatchObject({ from: "e7", to: "d8", promotion: "q", captured: "bR-d8" });
  });

  it("piece ids are unique per ply", () => {
    for (const g of all)
      for (const s of g.states) expect(new Set(s.pieces.map((p) => p.id)).size).toBe(s.pieces.length);
  });

  it("memoized (same array reference on second call)", () => {
    expect(buildPositions(games[1].pgn)).toBe(buildPositions(games[1].pgn));
  });
});
