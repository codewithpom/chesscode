import { describe, expect, it } from "vitest";
import { phaseAt, reactionsFor } from "../mascot/react";
import { coldOpenSpec, signOffBeats } from "../scenes/helpers";
import { sceneRanges } from "../scenes/timeline";
import { msToFrame } from "../spec/time";
import { GALLERY_SPECS, PANEL_TABLE } from "./TemplateGallery";

const FPS = 30;
const long = (lang: "en" | "hi") => GALLERY_SPECS[lang];

describe("gallery specs", () => {
  for (const lang of ["en", "hi"] as const) {
    const spec = long(lang);

    it(`${lang}: the 60 s spec has every scene, two-plus beats with an intensity-3 blunder that faints, and one key moment`, () => {
      expect(spec.duration_ms).toBe(60000);
      expect(sceneRanges(spec).map((r) => r.kind)).toEqual([
        "cold_open", "title", "player_intro", "playback", "key_moment", "playback", "verdict", "outro",
      ]);
      expect(spec.beats.length).toBeGreaterThanOrEqual(2);
      expect(spec.beats.find((b) => b.type === "blunder")).toMatchObject({ intensity: 3, mascot: { pose: "faint" } });
      expect(spec.key_moments).toHaveLength(1);
    });
  }

  it("Hindi narration, captions text, facts and labels are Devanagari", () => {
    const hi = long("hi");
    const dev = /[ऀ-ॿ]/;
    expect(hi.narration.every((n) => dev.test(n.text) && n.words.every((w) => w.w.length > 0))).toBe(true);
    expect([hi.game.white.fact, hi.game.black.fact, hi.key_moments[0].label, hi.cold_open.hook, hi.thumbnail.text].every((t) => dev.test(t))).toBe(true);
    expect(hi.language).toBe("hi");
  });
});

describe("gallery panels", () => {
  const wanted: Record<string, string> = {
    cold_open: "cold_open", title: "title", player_intro: "player_intro", playback: "playback",
    playback_blunder: "playback", key_moment: "key_moment", verdict: "verdict", outro: "outro",
  };

  for (const [name, p] of Object.entries(PANEL_TABLE)) {
    const spec = GALLERY_SPECS[p.spec];
    const frame = msToFrame(p.ms, FPS);

    it(`${name}: the moment is inside the spec and in the right scene`, () => {
      expect(p.ms).toBeLessThan(spec.duration_ms);
      if (p.kind === "studio") {
        const r = sceneRanges(spec).find((x) => p.ms >= x.startMs && p.ms < x.endMs)!;
        expect(r.kind).toBe(wanted[name.split("-")[0]]);
      }
    });

    const key = name.split("-")[0];
    if (key === "playback" || key === "cold_open" || key === "shorts_beat") {
      it(`${name}: a beat reaction and its bubble are on screen`, () => {
        // The cold open shows the beats of its own plies, moved into its range.
        const range = sceneRanges(spec)[0];
        const beats = key === "cold_open" ? coldOpenSpec(spec, range).beats : spec.beats;
        const rs = reactionsFor(beats, FPS, msToFrame(spec.duration_ms, FPS));
        expect(rs.some((r) => frame >= r.bubbleFrom && frame < r.bubbleTo)).toBe(true);
      });
    }
    if (key === "playback_blunder") {
      it(`${name}: Pyaada is mid-faint`, () => {
        const rs = reactionsFor(spec.beats, FPS, msToFrame(spec.duration_ms, FPS));
        expect(phaseAt(frame, rs, FPS)?.pose).toBe("faint");
      });
    }
    if (key === "outro") {
      it(`${name}: the sign-off bubble is up (point after wave)`, () => {
        const outro = sceneRanges(spec).find((r) => r.kind === "outro")!;
        const rs = reactionsFor(signOffBeats(spec, outro), FPS, msToFrame(spec.duration_ms, FPS));
        expect(rs.some((r) => frame >= r.bubbleFrom && frame < r.bubbleTo)).toBe(true);
      });
    }
  }

  it("has a still for every scene type in EN and HI, the Shorts hook and beat, and the thumbnail", () => {
    for (const lang of ["en", "hi"]) {
      for (const s of ["cold_open", "title", "player_intro", "playback", "key_moment", "verdict", "outro", "shorts_hook", "shorts_beat", "thumbnail"])
        expect(PANEL_TABLE[`${s}-${lang}`], `${s}-${lang}`).toBeDefined();
    }
  });
});
