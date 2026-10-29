import { describe, expect, it } from "vitest";
import { arrowGeometry } from "../board/Arrows";
import { cropViewBox, cropWindow, THUMB_ARROW_WIDTH } from "./Thumbnail";

describe("cropWindow", () => {
  it("White at the bottom: ranks top to bottom, files left to right, origin is the lower-left", () => {
    const w = cropWindow("a5", "white");
    expect(w).toHaveLength(16);
    expect(w.slice(0, 4)).toEqual(["a8", "b8", "c8", "d8"]);
    expect(w.slice(12)).toEqual(["a5", "b5", "c5", "d5"]);
    expect(w[12]).toBe("a5"); // lower-left on screen
  });

  it("Black at the bottom: the same squares turned 180 degrees, so the origin is the upper-right", () => {
    const w = cropWindow("a5", "black");
    expect(w).toHaveLength(16);
    expect(w.slice(0, 4)).toEqual(["d5", "c5", "b5", "a5"]);
    expect(w[3]).toBe("a5"); // upper-right on screen
    expect(w[12]).toBe("d8"); // lower-left on screen
    expect([...w].sort()).toEqual([...cropWindow("a5", "white")].sort());
  });

  it("an interior window, both orientations", () => {
    expect(cropWindow("c2", "white")[12]).toBe("c2");
    expect(cropWindow("c2", "white")[3]).toBe("f5");
    expect(cropWindow("c2", "black")[0]).toBe("f2");
    expect(cropWindow("c2", "black")[15]).toBe("c5");
  });

  it("rejects an origin whose window leaves the board", () => {
    expect(() => cropWindow("f1", "white")).toThrow();
    expect(() => cropWindow("a6", "white")).toThrow();
  });
});

describe("cropViewBox", () => {
  it("frames the window in oriented board units", () => {
    expect(cropViewBox("a5", "white")).toBe("0 0 4 4");
    expect(cropViewBox("e1", "white")).toBe("4 4 4 4");
    expect(cropViewBox("a5", "black")).toBe("4 4 4 4");
    expect(cropViewBox("e1", "black")).toBe("0 0 4 4");
  });
});

describe("thumbnail arrow", () => {
  const a = { from: "c3", to: "b5", color: "best" as const };
  it("the head stops at the target square's edge instead of burying the piece", () => {
    const centre = arrowGeometry(a, "white");
    const stopped = arrowGeometry(a, "white", 0.5);
    expect(Math.hypot(centre.x2 - stopped.x2, centre.y2 - stopped.y2)).toBeCloseTo(0.5, 6);
    // b5 centre is (1.5, 3.5) in white's view; the stopped tip is half a unit before it along the arrow.
    expect(Math.hypot(stopped.x2 - 1.5, stopped.y2 - 3.5)).toBeCloseTo(0.5, 6);
  });
  it("is thick enough to read at 320 x 180 (>= 24 px on the 480 px, 4-square crop)", () => {
    expect(THUMB_ARROW_WIDTH * (480 / 4)).toBeGreaterThanOrEqual(24);
  });
  it("follows orientation (Black at the bottom)", () => {
    const w = arrowGeometry(a, "white", 0.5);
    const b = arrowGeometry(a, "black", 0.5);
    expect(b.x1).toBeCloseTo(8 - w.x1, 6);
    expect(b.y1).toBeCloseTo(8 - w.y1, 6);
  });
});
