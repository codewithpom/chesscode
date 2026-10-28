import { describe, expect, it } from "vitest";
import { shortsLayout, youtubeShortsUi, type Box } from "./layout";

const boxes = Object.entries(shortsLayout.boxes) as Array<[string, Box]>;

describe("shortsLayout", () => {
  it("every box avoids the YouTube UI zones (right 120 px, bottom 340 px)", () => {
    for (const [name, b] of boxes) {
      expect(b.x + b.w, `${name} right edge`).toBeLessThanOrEqual(youtubeShortsUi.rightZoneX);
      expect(b.y + b.h, `${name} bottom edge`).toBeLessThanOrEqual(youtubeShortsUi.bottomZoneY);
      expect(b.x).toBeGreaterThanOrEqual(0);
      expect(b.y).toBeGreaterThanOrEqual(0);
    }
    expect(youtubeShortsUi.rightZoneX).toBe(shortsLayout.width - 120);
    expect(youtubeShortsUi.bottomZoneY).toBe(shortsLayout.height - 340);
  });

  it("uses the approved numbers", () => {
    const b = shortsLayout.boxes;
    expect(b.board).toEqual({ x: 48, y: 262, w: 864, h: 864 });
    expect(b.captions.y).toBe(72);
    expect([b.evalLabel.y, b.evalLabel.y + b.evalLabel.h]).toEqual([194, 222]);
    expect([b.evalBar.y, b.evalBar.y + b.evalBar.h]).toEqual([230, 246]);
    expect([b.mascot.y, b.mascot.y + b.mascot.h]).toEqual([1126, 1580]);
  });

  it("the vertical stack does not overlap: captions, eval label, eval bar, board, mascot", () => {
    const order = ["captions", "evalLabel", "evalBar", "board", "mascot"] as const;
    for (let i = 0; i < order.length - 1; i++) {
      const a = shortsLayout.boxes[order[i]];
      const next = shortsLayout.boxes[order[i + 1]];
      expect(a.y + a.h, `${order[i]} above ${order[i + 1]}`).toBeLessThanOrEqual(next.y);
    }
  });

  it("board coordinates stay inside x <= 960", () => {
    const { rankLabels, fileLabels } = shortsLayout.boxes;
    expect(rankLabels.x + rankLabels.w).toBeLessThanOrEqual(youtubeShortsUi.rightZoneX);
    expect(fileLabels.x + fileLabels.w).toBeLessThanOrEqual(youtubeShortsUi.rightZoneX);
  });
});
