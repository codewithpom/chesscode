// 20 fixture games for positions/board tests. Every move is validated by chess.js at replay.
// Feature coverage (asserted in positions.test.ts): castling both sides for both colors,
// en passant (both colors), promotion to queen, underpromotion to knight, capture-promotion with check.
const fen = (f: string, moves: string): string => `[SetUp "1"]\n[FEN "${f}"]\n\n${moves}`;

export type FixtureGame = { name: string; pgn: string };

export const games: FixtureGame[] = [
  {
    name: "opera game 1858 (spec fixture, queenside castle, mate)",
    pgn: `[Event "Paris Opera"]
[Site "Paris FRA"]
[Date "1858.11.02"]
[White "Paul Morphy"]
[Black "Duke Karl / Count Isouard"]
[Result "1-0"]
[ECO "C41"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7
8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7
14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0`,
  },
  { name: "scholar's mate", pgn: "1. e4 e5 2. Bc4 Nc6 3. Qh5 Nf6 4. Qxf7#" },
  { name: "fool's mate", pgn: "1. f3 e5 2. g4 Qh4#" },
  {
    name: "ruy lopez, both kingside castles",
    pgn: "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O",
  },
  {
    name: "both queenside castles",
    pgn: "1. d4 d5 2. Nc3 Nc6 3. Bf4 Bf5 4. Qd2 Qd7 5. O-O-O O-O-O",
  },
  {
    name: "white kingside, black queenside",
    pgn: "1. e4 d5 2. exd5 Qxd5 3. Nc3 Qd8 4. Nf3 Nc6 5. Bc4 Bg4 6. d3 Qd7 7. Be3 O-O-O 8. O-O",
  },
  {
    name: "white queenside, black kingside",
    pgn: "1. d4 Nf6 2. Nc3 g6 3. Bf4 Bg7 4. Qd2 O-O 5. O-O-O d6",
  },
  { name: "en passant by white", pgn: "1. e4 a6 2. e5 d5 3. exd6 Qxd6 4. Nf3" },
  { name: "en passant by black", pgn: "1. h3 d5 2. a3 d4 3. e4 dxe3 4. dxe3" },
  {
    name: "white promotes to queen with check",
    pgn: fen("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "1. a8=Q+ Kd7 2. Qb7+ Kd6"),
  },
  {
    name: "white underpromotes to knight with check",
    pgn: fen("8/5P1k/8/8/8/8/8/K7 w - - 0 1", "1. f8=N+ Kg7 2. Nd7 Kf7"),
  },
  {
    name: "capture-promotion with check (exd8=Q+)",
    pgn: fen("3rk3/4P3/8/8/8/8/8/4K3 w - - 0 1", "1. exd8=Q+ Kxd8 2. Kd2 Kc7"),
  },
  {
    name: "black promotes to queen with check",
    pgn: fen("4k3/8/8/8/8/8/p7/4K3 b - - 0 1", "1... a1=Q+ 2. Kd2 Qb2+ 3. Kd3"),
  },
  {
    name: "legal's mate",
    pgn: "1. e4 e5 2. Nf3 d6 3. Bc4 Bg4 4. Nc3 g6 5. Nxe5 Bxd1 6. Bxf7+ Ke7 7. Nd5#",
  },
  {
    name: "italian game, kingside castle",
    pgn: "1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6",
  },
  { name: "caro-kann smothered mate", pgn: "1. e4 c6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Nd7 5. Qe2 Ngf6 6. Nd6#" },
  {
    name: "scandinavian",
    pgn: "1. e4 d5 2. exd5 Qxd5 3. Nc3 Qa5 4. d4 c6 5. Nf3 Bf5 6. Bc4 e6 7. Bd2 Nf6",
  },
  {
    name: "queen's gambit declined, kingside castle",
    pgn: "1. d4 d5 2. c4 e6 3. Nc3 Nf6 4. Bg5 Be7 5. e3 O-O 6. Nf3 h6 7. Bh4 b6",
  },
  {
    name: "sicilian yugoslav, queenside castle",
    pgn: "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 g6 6. Be3 Bg7 7. f3 O-O 8. Qd2 Nc6 9. O-O-O",
  },
  {
    name: "king's indian, both kingside castles",
    pgn: "1. Nf3 Nf6 2. c4 g6 3. Nc3 Bg7 4. e4 d6 5. d4 O-O 6. Be2 e5 7. O-O Nc6 8. d5 Ne7",
  },
];
