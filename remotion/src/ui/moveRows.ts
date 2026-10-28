import type { Ply } from "../spec/schema";

export type MoveRow = { no: number; white?: string; black?: string; current: "w" | "b" | null };

/** Full-move rows of a game: ply 1 is row 1 white, ply 2 is row 1 black. */
export const allRows = (plies: Pick<Ply, "ply" | "san">[], currentPly: number): MoveRow[] => {
  const rows: MoveRow[] = [];
  for (const p of plies) {
    const no = Math.ceil(p.ply / 2);
    const row = (rows[no - 1] ??= { no, current: null });
    if (p.ply % 2 === 1) row.white = p.san;
    else row.black = p.san;
    if (p.ply === currentPly) row.current = p.ply % 2 === 1 ? "w" : "b";
  }
  return rows;
};

/** First visible row number: the current row centred, clamped so the window never runs past either end. */
export const windowStart = (totalRows: number, currentRow: number, visible = 9): number =>
  Math.max(1, Math.min(currentRow - Math.floor(visible / 2), totalRows - visible + 1));

/** The visible window (9 rows): the current move's row centred, clamped at the start and end of the game. */
export const moveRows = (plies: Pick<Ply, "ply" | "san">[], currentPly: number, visible = 9): MoveRow[] => {
  const rows = allRows(plies, currentPly);
  const first = windowStart(rows.length, Math.max(1, Math.ceil(currentPly / 2)), visible);
  return rows.slice(first - 1, first - 1 + visible);
};
