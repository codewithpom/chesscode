import { describe, expect, it } from "vitest";
import { BLIP_GAIN } from "../mascot/MascotLayer";
import { SFX_GAIN } from "./Sfx";

describe("audio balance", () => {
  it("blips are about a third of file level and beat sfx carry their level in the file", () => {
    expect(BLIP_GAIN).toBeGreaterThan(0.3);
    expect(BLIP_GAIN).toBeLessThanOrEqual(0.4);
    expect(SFX_GAIN).toBe(1);
  });
});
