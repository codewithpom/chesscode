import { describe, expect, it } from "vitest";
import { musicVolume } from "./musicVolume";

const music = { track: "music/x.mp3", volume: 0.12, duck_under_voice: 0.06 };
const narration = [{ start_ms: 1000, duration_ms: 2000 }, { start_ms: 5000, duration_ms: 1000 }];

describe("musicVolume", () => {
  it("is full volume in silence and ducked under the voice", () => {
    expect(musicVolume(0, narration, music)).toBe(0.12);
    expect(musicVolume(2000, narration, music)).toBe(0.06);
    expect(musicVolume(4000, narration, music)).toBe(0.12);
  });
  it("ramps over 200 ms, finishing as the voice starts and starting when it ends", () => {
    expect(musicVolume(900, narration, music)).toBeCloseTo(0.09);
    expect(musicVolume(1000, narration, music)).toBeCloseTo(0.06);
    expect(musicVolume(3100, narration, music)).toBeCloseTo(0.09);
    expect(musicVolume(3200, narration, music)).toBeCloseTo(0.12);
  });
  it("never goes outside [duck, volume]", () => {
    for (let ms = 0; ms < 8000; ms += 37) {
      const v = musicVolume(ms, narration, music);
      expect(v).toBeGreaterThanOrEqual(0.06 - 1e-9);
      expect(v).toBeLessThanOrEqual(0.12 + 1e-9);
    }
  });
});
