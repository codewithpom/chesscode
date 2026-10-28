import { describe, expect, it } from "vitest";
import fixture from "../../../spec/fixtures/cc-2026-0001-en/video_spec.json";
import { REEL_SPEC } from "../compositions/MascotReel";
import { VideoSpec } from "../spec/schema";
import { shortsLayout, type Box } from "../theme/layout";
import { estimateLines, layerRects, mascotWidth, textHeight } from "./layerLayout";
import { poseAt, reactionsFor } from "./react";
import { BUBBLE_FONT } from "./speech";

const FPS = 30;
const inside = (inner: Box, outer: Box) =>
  inner.x >= outer.x && inner.y >= outer.y && inner.x + inner.w <= outer.x + outer.w && inner.y + inner.h <= outer.y + outer.h;
const overlap = (a: Box, b: Box) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

const BOXES: Array<[string, Box, number]> = [
  ["studio", { x: 1000, y: 696, w: 824, h: 288 }, 200],
  ["shorts", shortsLayout.boxes.mascot, 260],
];
const HI_10 = "यह चाल देखकर प्यादा भी सोच में पड़ गया, भाई";

describe("MascotLayer layout", () => {
  for (const [name, box, height] of BOXES) {
    const { mascot, bubble } = layerRects(box, height);

    it(`${name}: mascot and bubble sit inside the box and never overlap`, () => {
      expect(inside(mascot, box)).toBe(true);
      expect(inside(bubble, box)).toBe(true);
      expect(overlap(mascot, bubble)).toBe(false);
      expect(BUBBLE_FONT).toBeGreaterThanOrEqual(28);
    });

    it(`${name}: for every beat frame the mascot stays in the box (faint leaves only by its own slide, clipped)`, () => {
      const specs = [VideoSpec.parse(fixture), REEL_SPEC];
      const scale = height / 260;
      for (const spec of specs) {
        const rs = reactionsFor(spec.beats, FPS, 1800);
        for (const r of rs) {
          for (let f = r.freezeFrom; f <= r.bubbleTo; f++) {
            const s = poseAt(f, rs, FPS, spec.video_id);
            const shift = s.offsetX * scale;
            if (r.beat.mascot.pose === "faint") continue; // slides out through the clip edge, back in by +57 frames
            expect(Math.abs(shift)).toBeLessThanOrEqual(0.04 * mascotWidth(height));
          }
        }
      }
    });

    it(`${name}: a 10-word Hindi line and the longest English line fit the bubble`, () => {
      for (const line of [HI_10, "Never mind, he's back!", "Two pieces. That's all he needed."]) {
        expect(textHeight(estimateLines(line, bubble.w))).toBeLessThanOrEqual(bubble.h);
      }
      expect(HI_10.split(" ")).toHaveLength(10);
    });
  }

  it("faint slides out and back within 57 frames of the reaction", () => {
    const rs = reactionsFor(REEL_SPEC.beats, FPS, 600);
    const r = rs[0];
    expect(poseAt(r.reactFrame + 20, rs, FPS, "s").offsetX).toBeGreaterThan(200);
    expect(poseAt(r.reactFrame + 57, rs, FPS, "s").offsetX).toBe(0);
  });
});
