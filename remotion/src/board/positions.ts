import { Chess } from "chess.js";

export type PieceType = "p" | "n" | "b" | "r" | "q" | "k";
/** Stable per physical piece for the whole game, e.g. "wN-g1" (color, start type, start square). */
export type PieceId = string;
export type PlacedPiece = { id: PieceId; type: PieceType; color: "w" | "b"; square: string };
export type PlyMove = {
  from: string;
  to: string;
  captured: PieceId | null;
  castleRook: { id: PieceId; from: string; to: string } | null;
  promotion: "q" | "r" | "b" | "n" | null;
  /** Square the en-passant-captured pawn stood on (not the destination square). */
  enPassantSquare: string | null;
};
/** Index 0 is the start position (move null); `pieces` is the board after the move. */
export type PlyState = { fen: string; pieces: PlacedPiece[]; move: PlyMove | null };

const startPieces = (fen: string): PlacedPiece[] => {
  const out: PlacedPiece[] = [];
  fen
    .split(" ")[0]
    .split("/")
    .forEach((row, r) => {
      let file = 0;
      for (const ch of row) {
        if (/\d/.test(ch)) file += Number(ch);
        else {
          const color = ch === ch.toUpperCase() ? "w" : "b";
          const square = String.fromCharCode(97 + file) + (8 - r);
          out.push({ id: `${color}${ch.toUpperCase()}-${square}`, type: ch.toLowerCase() as PieceType, color, square });
          file++;
        }
      }
    });
  return out;
};

const byId = (a: PlacedPiece, b: PlacedPiece): number => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
const cache = new Map<string, PlyState[]>();

/** Replays the PGN once with chess.js; memoized by PGN string. */
export const buildPositions = (pgn: string): PlyState[] => {
  const hit = cache.get(pgn);
  if (hit) return hit;

  const parsed = new Chess();
  parsed.loadPgn(pgn);
  const startFen = new Chess(parsed.getHeaders().FEN ?? undefined).fen();
  const history = parsed.history({ verbose: true });

  const board = new Map<string, PlacedPiece>(startPieces(startFen).map((p) => [p.square, p]));
  const snapshot = (): PlacedPiece[] => Array.from(board.values()).map((p) => ({ ...p })).sort(byId);
  const states: PlyState[] = [{ fen: startFen, pieces: snapshot(), move: null }];

  for (const m of history) {
    const mover = board.get(m.from)!;
    board.delete(m.from);

    const enPassantSquare = m.isEnPassant() ? m.to[0] + m.from[1] : null;
    const capSquare = enPassantSquare ?? m.to;
    const capturedPiece = m.captured ? board.get(capSquare)! : null;
    if (capturedPiece) board.delete(capSquare);

    let castleRook: PlyMove["castleRook"] = null;
    if (m.isKingsideCastle() || m.isQueensideCastle()) {
      const rank = m.from[1];
      const from = (m.isKingsideCastle() ? "h" : "a") + rank;
      const to = (m.isKingsideCastle() ? "f" : "d") + rank;
      const rook = board.get(from)!;
      board.delete(from);
      board.set(to, { ...rook, square: to });
      castleRook = { id: rook.id, from, to };
    }

    mover.square = m.to;
    if (m.promotion) mover.type = m.promotion;
    board.set(m.to, mover);

    states.push({
      fen: m.after,
      pieces: snapshot(),
      move: {
        from: m.from,
        to: m.to,
        captured: capturedPiece?.id ?? null,
        castleRook,
        promotion: (m.promotion as PlyMove["promotion"]) ?? null,
        enPassantSquare,
      },
    });
  }

  cache.set(pgn, states);
  return states;
};
