import { describe, expect, it } from "vitest";
import { formatClock } from "./Clock";
import { moveRows, windowStart } from "./moveRows";

const plies = Array.from({ length: 41 }, (_, i) => ({ ply: i + 1, san: `m${i + 1}` })); // 21 rows, last is white only

describe("moveRows", () => {
  it("lists only the moves played: at the start one row, the rest of the window stays empty", () => {
    const rows = moveRows(plies, 1);
    expect(rows).toEqual([{ no: 1, white: "m1", current: "w" }]); // m2 (Black's reply) is not played yet
  });

  it("never shows a move later than the current one, anywhere in the game", () => {
    for (let cur = 0; cur <= plies.length; cur++) {
      const shown = moveRows(plies, cur).flatMap((r) => [r.white, r.black]).filter(Boolean) as string[];
      for (const san of shown) expect(Number(san.slice(1)), `ply ${cur}`).toBeLessThanOrEqual(cur);
    }
  });

  it("before the first move nothing is listed", () => {
    expect(moveRows(plies, 0)).toEqual([]);
  });

  it("the first rows fill in as the game goes on, white's half first", () => {
    expect(moveRows(plies, 2)).toEqual([{ no: 1, white: "m1", black: "m2", current: "b" }]);
    expect(moveRows(plies, 7).map((r) => r.no)).toEqual([1, 2, 3, 4]);
    expect(moveRows(plies, 7)[3]).toEqual({ no: 4, white: "m7", current: "w" });
  });

  it("centres the current row in the middle of a game, with the unplayed rows below it empty", () => {
    const rows = moveRows(plies, 24); // ply 24 = row 12 black
    expect(rows.map((r) => r.no)).toEqual([8, 9, 10, 11, 12]);
    expect(rows[4]).toMatchObject({ no: 12, current: "b" });
  });

  it("clamps at the end of the game", () => {
    const rows = moveRows(plies, 41);
    expect(rows.map((r) => r.no)).toEqual([13, 14, 15, 16, 17, 18, 19, 20, 21]);
    expect(rows[8]).toEqual({ no: 21, white: "m41", current: "w" });
  });

  it("windowStart: a game shorter than the window starts at row 1", () => {
    expect(windowStart(3, 2)).toBe(1);
  });
});

describe("formatClock", () => {
  it("is m:ss", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(59_999)).toBe("0:59");
    expect(formatClock(605_000)).toBe("10:05");
  });
});
