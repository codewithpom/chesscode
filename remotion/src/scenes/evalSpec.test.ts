import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { VideoSpec } from "../spec/schema";
import { templateFx } from "../theme/templates";
import { barShareAt } from "../ui/winprob";
import { evalSpec } from "./StudioBoard";

const spec = VideoSpec.parse(
  JSON.parse(readFileSync(resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"), "utf8")),
);
const comeback = { ...spec.beats[0], type: "comeback" as const, ply: 20, fx: ["eval_whip" as const] };
const withBeat = { ...spec, beats: [comeback] };
const frame = Math.round((spec.plies[19].show_at_ms * 30) / 1000) + 4;
const share = (s: VideoSpec) => barShareAt(frame, 30, s.plies, s.beats);

describe("evalSpec", () => {
  it("passes a comeback's eval_whip through to the bar while the template allows it", () => {
    expect(share(evalSpec(withBeat, "studio"))).toBe(share(withBeat));
    expect(share(withBeat)).not.toBe(share({ ...spec, beats: [] }));
  });

  it("the template's eval_whip off switch removes the whip", () => {
    templateFx.shorts.eval_whip = false;
    try {
      expect(share(evalSpec(withBeat, "shorts"))).toBe(share({ ...spec, beats: [] }));
      expect(share(evalSpec(withBeat, "studio"))).toBe(share(withBeat));
    } finally {
      templateFx.shorts.eval_whip = true;
    }
  });
});
