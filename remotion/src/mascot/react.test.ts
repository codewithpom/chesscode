import { describe, expect, it } from "vitest";
import type { Beat } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { blinkStarts } from "./idle";
import { freezeAt, phaseAt, poseAt, reactionsFor } from "./react";

const FPS = 30;
const beat = (id: string, at_ms: number, intensity: 1 | 2 | 3, pose: Beat["mascot"]["pose"], line = "Oh no, not again.", type: Beat["type"] = "blunder"): Beat => ({
  beat_id: id, type, ply: 10, at_ms, intensity, mascot: { pose, line }, fx: [], sfx: null,
});

describe("reactionsFor", () => {
  it("applies the comic timing for an intensity 3 beat", () => {
    const line = "Two pieces, that is all.";
    const [r] = reactionsFor([beat("a", 10_000, 3, "faint", line)], FPS, 3000);
    expect([r.freezeFrom, r.freezeTo, r.reactFrame, r.bubbleFrom]).toEqual([300, 306, 306, 309]);
    expect(r.bubbleTo - r.bubbleFrom).toBe(54 + msToFrame(60 * [...line].length, FPS));
  });

  it("intensity 1 reacts at at_ms with no freeze", () => {
    const [r] = reactionsFor([beat("a", 10_000, 1, "side_eye")], FPS, 3000);
    expect([r.freezeFrom, r.freezeTo, r.reactFrame]).toEqual([300, 300, 300]);
    expect(r.bubbleFrom).toBe(303);
  });

  it("never yields negative or out-of-video frames (beat at 0 and in the last 2 s)", () => {
    const rs = reactionsFor([beat("a", 0, 3, "facepalm"), beat("b", 58_500, 3, "mic_drop")], FPS, 1800);
    for (const r of rs) {
      for (const f of [r.freezeFrom, r.freezeTo, r.reactFrame, r.bubbleFrom, r.bubbleTo]) {
        expect(f).toBeGreaterThanOrEqual(0);
        expect(f).toBeLessThanOrEqual(1800);
      }
      expect(r.bubbleTo).toBeGreaterThanOrEqual(r.bubbleFrom);
    }
    expect(poseAt(0, rs, FPS, "s").eyeOpen).toBeGreaterThanOrEqual(0);
    expect(() => poseAt(1800, rs, FPS, "s")).not.toThrow();
  });

  it("ends the first bubble before the second reaction when beats are 20 s apart", () => {
    const long = "A very long line that would otherwise run on for a long while, ok";
    const [a, b] = reactionsFor([beat("a", 10_000, 1, "side_eye", long), beat("b", 30_000, 3, "facepalm")], FPS, 3000);
    expect(a.bubbleTo).toBeLessThan(b.reactFrame);
    expect(a.bubbleTo).toBeGreaterThan(a.bubbleFrom);
    // And a close pair is clamped.
    const [c, d] = reactionsFor([beat("c", 10_000, 1, "side_eye", long), beat("d", 10_500, 1, "wave")], FPS, 3000);
    expect(c.bubbleTo).toBeLessThan(d.reactFrame);
  });
});

describe("freezeAt", () => {
  it("holds the frame during the freeze only", () => {
    const rs = reactionsFor([beat("a", 10_000, 3, "faint")], FPS, 3000);
    expect(freezeAt(299, rs)).toBeNull();
    expect(freezeAt(300, rs)).toBe(300);
    expect(freezeAt(305, rs)).toBe(300);
    expect(freezeAt(306, rs)).toBeNull();
  });
});

describe("poseAt", () => {
  it("is deterministic and idle before the first reaction", () => {
    const rs = reactionsFor([beat("a", 10_000, 3, "facepalm")], FPS, 3000);
    expect(poseAt(100, rs, FPS, "s")).toEqual(poseAt(100, rs, FPS, "s"));
    expect(poseAt(100, rs, FPS, "s").arms).toBe("none");
    expect(poseAt(380, rs, FPS, "s").arms).toBe("face");
  });

  it("faint tips back, falls out of frame with ease-in, and is back in by reactFrame + 45 + 12", () => {
    const rs = reactionsFor([beat("a", 10_000, 3, "faint")], FPS, 3000);
    const react = rs[0].reactFrame;
    const at = (f: number) => poseAt(react + f, rs, FPS, "s");
    expect(at(0).offsetY).toBeLessThan(2); // idle bob only
    expect(at(4).lean).toBeCloseTo(-25, 0); // anticipation
    expect(at(10).offsetY).toBeLessThan(at(14).offsetY - 60); // accelerating
    expect(at(16).offsetY).toBeGreaterThan(500);
    expect(at(16).lean).toBeCloseTo(90, 0);
    expect(at(44).offsetY).toBeGreaterThan(500);
    expect(at(45 + 12).offsetY).toBeLessThan(2);
    expect(at(45 + 12).offsetX).toBe(0);
    expect(at(45 + 12).lean).toBeCloseTo(0, 6);
    expect(rs[0].bubbleTo).toBeGreaterThan(react + 57);
  });

  it("faint re-entry finishes before the next beat's pose", () => {
    const rs = reactionsFor([beat("a", 10_000, 3, "faint"), beat("b", 30_000, 1, "side_eye")], FPS, 3000);
    const s = poseAt(rs[1].reactFrame, rs, FPS, "s");
    expect(Math.abs(s.offsetX)).toBeLessThan(1);
    expect(Math.abs(s.lean)).toBeLessThan(1);
  });
});

describe("comeback: shocked, then party", () => {
  const rs = reactionsFor([beat("c", 10_000, 2, "shocked", "Never mind, he is back!", "comeback")], FPS, 3000);
  const react = rs[0].reactFrame;

  it("is shocked first and celebrates 1.2 s later", () => {
    expect(phaseAt(react, rs, FPS)).toMatchObject({ pose: "shocked", start: react });
    expect(phaseAt(react + 35, rs, FPS)?.pose).toBe("shocked");
    expect(phaseAt(react + 36, rs, FPS)).toMatchObject({ pose: "party", start: react + 36, beatId: "c" });
    expect(phaseAt(rs[0].bubbleTo, rs, FPS)).toBeNull();
    const shocked = poseAt(react + 30, rs, FPS, "s");
    expect([shocked.mouth, shocked.arms, shocked.prop]).toEqual(["o", "none", "crown"]);
    const party = poseAt(react + 36 + 30, rs, FPS, "s");
    expect([party.arms, party.prop]).toEqual(["up", "party_hat"]);
  });

  it("only a comeback with the default shocked pose gets the second phase", () => {
    const other = reactionsFor([beat("d", 10_000, 2, "shocked", "Oh.", "blunder")], FPS, 3000);
    expect(phaseAt(other[0].reactFrame + 60, other, FPS)?.pose).toBe("shocked");
  });
});

describe("blinks and spring", () => {
  it("does not blink in the first 30 frames of a reaction, but does when idle", () => {
    const [blink] = blinkStarts(900, FPS, "s");
    const idleRs = reactionsFor([], FPS, 3000);
    expect(poseAt(blink + 1, idleRs, FPS, "s").eyeOpen).toBe(0);
    // thinking has open eyes; start its reaction 5 frames before the blink.
    const rs = reactionsFor([beat("a", ((blink - 5) * 1000) / FPS, 1, "thinking")], FPS, 3000);
    expect(rs[0].reactFrame).toBe(blink - 5);
    expect(poseAt(blink + 1, rs, FPS, "s").eyeOpen).toBe(1);
    expect(poseAt(blink + 31, rs, FPS, "s").eyeOpen).toBeGreaterThan(0.5); // blinks are back after 30 frames (none due here)
  });

  it("is 90% of the way into the pose 8 frames after the reaction (frame-7 snap)", () => {
    const rs = reactionsFor([beat("a", 10_000, 1, "shocked")], FPS, 3000);
    const at = rs[0].reactFrame;
    expect(poseAt(at + 8, rs, FPS, "s").eyeScale).toBeGreaterThan(1 + 0.18 * 0.9);
    expect(poseAt(at + 1, rs, FPS, "s").eyeScale).toBeLessThan(1 + 0.18 * 0.2);
  });
});
