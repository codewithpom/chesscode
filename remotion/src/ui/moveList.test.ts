import { describe, expect, it } from "vitest";
import { formatClock } from "./Clock";
import { moveRows, windowStart } from "./moveRows";

const plies = Array.from({ length: 41 }, (_, i) => ({ ply: i + 1, san: `m${i + 1}` })); // 21 rows, last is white only

describe("moveRows", () => {
  it("starts at row 1 with the first move current (window clamped at the start)", () => {
    const rows = moveRows(plies, 1);
    expect(rows.map((r) => r.no)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
    expect(rows[0]).toEqual({ no: 1, white: "m1", black: "m2", current: "w" });
  });

  it("before the first move nothing is current", () => {
    expect(moveRows(plies, 0).every((r) => r.current === null)).toBe(true);
  });

  it("centres the current row in the middle of a game", () => {
    const rows = moveRows(plies, 24); // ply 24 = row 12 black
    expect(rows.map((r) => r.no)).toEqual([8, 9, 10, 11, 12, 13, 14, 15, 16]);
    expect(rows[4]).toMatchObject({ no: 12, current: "b" });
  });

  it("clamps at the end and keeps a half row", () => {
    const rows = moveRows(plies, 41);
    expect(rows.map((r) => r.no)).toEqual([13, 14, 15, 16, 17, 18, 19, 20, 21]);
    expect(rows[8]).toEqual({ no: 21, white: "m41", current: "w" });
  });

  it("a game shorter than the window shows all rows", () => {
    expect(moveRows(plies.slice(0, 5), 3)).toHaveLength(3);
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
