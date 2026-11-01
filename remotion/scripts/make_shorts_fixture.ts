// Hand-derives the Shorts fixture from the Opera Game Studio fixture (scripts/make_fixture.py has no Shorts mode):
//   npx tsx scripts/make_shorts_fixture.ts
// The Short is the finish: plies 1-31 snap onto the board at frame 0, then plies 32 and 33 (checkmate, the one beat)
// play over two narration segments, so the loop has to ease the final position back to the opening one.
// Audio is the fixture's silent MP3s. The result is validated by the Zod schema before it is written.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { VideoSpec } from "../src/spec/schema";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const from = resolve(root, "spec/fixtures/cc-2026-0001-en");
const to = resolve(root, "spec/fixtures/cc-2026-0002-en");
const base = VideoSpec.parse(JSON.parse(readFileSync(resolve(from, "video_spec.json"), "utf8")));

const [segA, segB] = [base.narration[6], base.narration[7]]; // ply 31 and ply 33 narration of the fixture
const START_B = segA.duration_ms + 300; // the pipeline's segment gap
const shift = (s: typeof segA, start_ms: number, segment_id: string, audio: string) => ({
  ...s,
  segment_id,
  audio,
  start_ms,
  words: s.words.map((w) => ({ ...w, start_ms: w.start_ms - s.start_ms + start_ms, end_ms: w.end_ms - s.start_ms + start_ms })),
});
const narration = [shift(segA, 0, "en_seg-000", "audio/en_seg-000.mp3"), shift(segB, START_B, "en_seg-001", "audio/en_seg-001.mp3")];
const duration_ms = START_B + segB.duration_ms; // a Short has no outro

const midWord = narration[0].words[Math.floor(narration[0].words.length / 2)].start_ms;
const showAt = (ply: number) => (ply <= 31 ? 0 : ply === 32 ? midWord : START_B);
const plies = base.plies.map((p) => ({ ...p, show_at_ms: showAt(p.ply) }));
const mate = base.beats.find((b) => b.type === "checkmate")!;

const spec = VideoSpec.parse({
  ...base,
  video_id: "cc-2026-0002-en",
  pair_id: "cc-2026-0002",
  template: "shorts",
  format: { width: 1080, height: 1920, fps: 30 },
  duration_ms,
  plies,
  narration,
  beats: [{ ...mate, beat_id: "b-01", at_ms: START_B }],
  chapters: [{ title: "The finish", start_ms: 0 }],
  key_moments: [],
  music: { ...base.music, track: "music/bed_calm_01.mp3" },
});

mkdirSync(resolve(to, "audio"), { recursive: true });
mkdirSync(resolve(to, "music"), { recursive: true });
copyFileSync(resolve(from, "audio/en_seg-006.mp3"), resolve(to, "audio/en_seg-000.mp3"));
copyFileSync(resolve(from, "audio/en_seg-007.mp3"), resolve(to, "audio/en_seg-001.mp3"));
copyFileSync(resolve(from, "music/bed_calm_01.mp3"), resolve(to, "music/bed_calm_01.mp3"));
writeFileSync(resolve(to, "video_spec.json"), JSON.stringify(spec, null, 2) + "\n");
console.log(`wrote ${to} (${duration_ms} ms)`);
