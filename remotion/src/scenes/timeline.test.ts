import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { VideoSpec } from "../spec/schema";
import { chapterCardsFor, sceneRanges } from "./timeline";

const fixture = VideoSpec.parse(
  JSON.parse(readFileSync(resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"), "utf8")),
);

const seg = (kind: string, start_ms: number, duration_ms: number, ply: number | null = null, i = 0) => ({
  ...fixture.narration[1],
  segment_id: `s${i}`,
  kind: kind as VideoSpec["narration"][number]["kind"],
  ply,
  start_ms,
  duration_ms,
  words: [{ w: "x", start_ms, end_ms: start_ms + 100 }],
});

// Long-form script order from the pipeline: cold open, title, intro, plies, key moment, verdict, outro.
const full = VideoSpec.parse({
  ...fixture,
  duration_ms: 100000,
  narration: [
    seg("cold_open", 0, 5000, null, 0),
    seg("title", 5300, 2500, null, 1),
    seg("player_intro", 8100, 6000, null, 2),
    seg("ply", 14400, 20000, 1, 3),
    seg("key_moment", 35000, 18000, 7, 4),
    seg("ply", 53300, 20000, 13, 5),
    seg("verdict", 73600, 10000, null, 6),
    seg("outro", 84000, 6000, null, 7),
  ],
  key_moments: [
    { beat_id: "b-01", ply: 7, start_ms: 35000, duration_ms: 18000, label: "Out of theory", line: ["e7e5"] },
  ],
});

const expectSound = (spec: VideoSpec) => {
  const r = sceneRanges(spec);
  expect(r[0].startMs).toBe(0);
  expect(r[r.length - 1].endMs).toBe(spec.duration_ms);
  r.forEach((x, i) => {
    expect(x.endMs, `${x.kind} #${i} not empty`).toBeGreaterThan(x.startMs);
    if (i) expect(x.startMs, `${x.kind} #${i} contiguous`).toBe(r[i - 1].endMs);
  });
  return r;
};

describe("sceneRanges", () => {
  it("covers the Opera fixture contiguously with no empty scene", () => {
    const r = expectSound(fixture);
    expect(r.map((x) => x.kind)).toEqual(["cold_open", "playback", "outro"]);
    expect(r[0].endMs).toBe(5400); // the cold open owns the gap up to the first ply segment
    expect(r[2].startMs).toBe(40000); // synthesised outro after the last narration
  });

  it("cuts a full script into its scenes and key moments", () => {
    const r = expectSound(full);
    expect(r.map((x) => [x.kind, x.startMs, x.endMs])).toEqual([
      ["cold_open", 0, 5300],
      ["title", 5300, 8100],
      ["player_intro", 8100, 14400],
      ["playback", 14400, 35000],
      ["key_moment", 35000, 53000],
      ["playback", 53000, 73600],
      ["verdict", 73600, 84000],
      ["outro", 84000, 100000],
    ]);
  });

  it("maps every key moment to one key_moment range with matching ms", () => {
    const km = sceneRanges(full).filter((x) => x.kind === "key_moment");
    expect(km).toHaveLength(full.key_moments.length);
    km.forEach((x, i) => {
      expect(x.startMs).toBe(full.key_moments[i].start_ms);
      expect(x.endMs).toBe(full.key_moments[i].start_ms + full.key_moments[i].duration_ms);
      expect(x.keyMoment).toBe(full.key_moments[i]);
    });
  });

  it("a short script without verdict, intro or key moments makes no empty scene", () => {
    const miniature = VideoSpec.parse({ ...fixture, narration: [fixture.narration[0], ...fixture.narration.slice(1, 3)], duration_ms: 20000 });
    expect(expectSound(miniature).map((x) => x.kind)).toEqual(["cold_open", "playback", "outro"]);
  });

  it("a later scene wins an overlap instead of leaving a zero-length range", () => {
    const early = { ...full, key_moments: [{ ...full.key_moments[0], start_ms: 6000 }] };
    const r = expectSound(early);
    expect(r.find((x) => x.kind === "title")).toMatchObject({ startMs: 5300, endMs: 6000 });
    expect(r.find((x) => x.kind === "player_intro")).toBeUndefined();
  });
});

describe("chapterCardsFor", () => {
  it("is every chapter after the first", () => {
    expect(chapterCardsFor(fixture)).toEqual([
      { title: "The attack", startMs: 20400 },
      { title: "The finish", startMs: 30000 },
    ]);
  });

  it("a one-chapter game has no cards", () => {
    expect(chapterCardsFor({ ...fixture, chapters: [fixture.chapters[0]] })).toEqual([]);
  });

  it("makes no card for a chapter that starts inside another scene", () => {
    const inKeyMoment = { ...full, chapters: [{ title: "Opening", start_ms: 0 }, { title: "Inside", start_ms: 40000 }, { title: "Late", start_ms: 60000 }] };
    expect(chapterCardsFor(inKeyMoment)).toEqual([{ title: "Late", startMs: 60000 }]);
  });
});
