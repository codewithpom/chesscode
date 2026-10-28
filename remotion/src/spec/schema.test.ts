import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { VideoSpec } from "./schema";
import { frameToMs, msToFrame } from "./time";

const fixture = JSON.parse(
  readFileSync(resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"), "utf8"),
);

describe("VideoSpec", () => {
  it("accepts the contract fixture", () => {
    expect(VideoSpec.safeParse(fixture).success).toBe(true);
  });
  it("rejects an unknown major version", () => {
    expect(VideoSpec.safeParse({ ...fixture, spec_version: "2.0.0" }).success).toBe(false);
  });
  it("rejects an eval with both cp and mate", () => {
    const plies = [{ ...fixture.plies[0], eval: { cp: 10, mate: 2 } }, ...fixture.plies.slice(1)];
    expect(VideoSpec.safeParse({ ...fixture, plies }).success).toBe(false);
  });
  it("rejects shorts that are not 1080x1920", () => {
    expect(VideoSpec.safeParse({ ...fixture, template: "shorts" }).success).toBe(false);
  });
  it("rejects overlapping narration", () => {
    const narration = [...fixture.narration];
    narration[1] = { ...narration[1], start_ms: narration[0].start_ms + 10 };
    expect(VideoSpec.safeParse({ ...fixture, narration }).success).toBe(false);
  });
  it("rejects absolute asset paths", () => {
    expect(VideoSpec.safeParse({ ...fixture, music: { ...fixture.music, track: "/etc/x.mp3" } }).success).toBe(false);
  });
});

describe("msToFrame", () => {
  it("rounds ms to the nearest frame and round-trips frames", () => {
    expect(msToFrame(41200, 30)).toBe(1236);
    expect(msToFrame(17, 30)).toBe(1);
    for (let f = 0; f < 3000; f++) expect(msToFrame(frameToMs(f, 30), 30)).toBe(f);
  });
});

describe("contract 1.1 scene data", () => {
  it("rejects a cold open that runs backwards", () => {
    expect(VideoSpec.safeParse({ ...fixture, cold_open: { ...fixture.cold_open, ply_from: 33, ply_to: 31 } }).success).toBe(false);
  });
  it("rejects thumbnail text over four words or equal to the title", () => {
    expect(VideoSpec.safeParse({ ...fixture, thumbnail: { ...fixture.thumbnail, text: "one two three four five" } }).success).toBe(false);
    expect(VideoSpec.safeParse({ ...fixture, thumbnail: { ...fixture.thumbnail, text: "Same" }, youtube: { ...fixture.youtube, title: "same" } }).success).toBe(false);
  });
  it("rejects a key moment that references no beat", () => {
    const km = { beat_id: "nope", ply: 31, start_ms: 30000, duration_ms: 15000, label: "The queen sac", line: ["b3b8"] };
    expect(VideoSpec.safeParse({ ...fixture, key_moments: [km] }).success).toBe(false);
    expect(VideoSpec.safeParse({ ...fixture, key_moments: [{ ...km, beat_id: "b-02" }] }).success).toBe(true);
  });
});
