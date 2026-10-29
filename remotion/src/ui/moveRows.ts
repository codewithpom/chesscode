import type { Ply } from "../spec/schema";

export type MoveRow = { no: number; white?: string; black?: string; current: "w" | "b" | null };

/** Rows of the moves played so far (plies up to `currentPly`, never a later one): ply 1 is row 1 white, ply 2 is row 1 black. */
export const allRows = (plies: Pick<Ply, "ply" | "san">[], currentPly: number): MoveRow[] => {
  const rows: MoveRow[] = [];
  for (const p of plies) {
    if (p.ply > currentPly) continue;
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

/** Rows of the whole game, which fixes where the window sits. */
export const totalRows = (plies: Pick<Ply, "ply">[]): number => Math.ceil(plies.length / 2);

/**
 * The visible window (up to 9 rows): the current move's row centred, clamped at the start and end of the game.
 * Only moves already played are listed, so a window near the start has fewer rows and the rest stay empty.
 */
export const moveRows = (plies: Pick<Ply, "ply" | "san">[], currentPly: number, visible = 9): MoveRow[] => {
  const first = windowStart(totalRows(plies), Math.max(1, Math.ceil(currentPly / 2)), visible);
  return allRows(plies, currentPly).slice(first - 1, first - 1 + visible);
};
