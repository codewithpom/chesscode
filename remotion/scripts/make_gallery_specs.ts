// Synthetic specs for the TemplateGallery and the 60 s Studio clip (Task 8), derived from the Opera Game fixture:
//   npx tsx scripts/make_gallery_specs.ts
// writes spec/fixtures/gallery-{en,hi}/ (60 s long-form: cold open, title, player intro, playback with a faint-worthy
// blunder and a brilliant beat, one key moment, verdict, outro) and gallery-short-{en,hi}/ (the mate finish as a Short).
// Audio is the fixture's silent MP3. Every spec is validated by the Zod schema before it is written. The Hindi is
// written for layout review (Devanagari at real sizes); the owner should review the wording before anything ships.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { lineStates } from "../src/board/positions";
import { VideoSpec } from "../src/spec/schema";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const fixtureDir = resolve(root, "spec/fixtures/cc-2026-0001-en");
const base = VideoSpec.parse(JSON.parse(readFileSync(resolve(fixtureDir, "video_spec.json"), "utf8")));

type Lang = "en" | "hi";
const T = {
  en: {
    title: "He gave up his queen at the opera (and mated in 17)",
    hook: "A queen sacrifice at the opera",
    facts: ["Unofficial world's best player at 21, retired from chess at 22.", "Two noblemen consulting on every move, in their own opera box."],
    cold: "One queen sacrifice. Two pieces left. A mate people still study.",
    titleSeg: "Morphy against the two noblemen, Paris, 1858.",
    intro: "A young American genius against a duke and a count who think they can help each other.",
    ply1: "Morphy opens with the king's pawn, and the nobles answer in kind.",
    ply7: "Black pins the knight early, and White trades off the pin.",
    ply12: "Black develops the knight.",
    km: "Here Black had a quieter way: queen to d7, and White's attack takes much longer to arrive.",
    ply13: "Queen to b3 hits f7 and b7 at once.",
    verdict: "Morphy played nearly perfectly. His opponents did not come close.",
    outro: "Thanks for watching.",
    lineBlunder: "Not the knight, surely?",
    lineBrilliant: "Now that is a sacrifice.",
    label: "A quieter way",
    chapters: ["The opening", "The attack", "The finish"],
    thumb: "Knight sac, wins",
    shortA: "Queen to b8, check! Black has to take it.",
    shortB: "Rook to d8. Mate. Two pieces were enough.",
    lineMate: "Two pieces. That's all he needed.",
  },
  hi: {
    title: "ओपेरा में वज़ीर कुर्बान, 17 चालों में मात",
    hook: "ओपेरा में वज़ीर की कुर्बानी",
    facts: ["21 की उम्र में दुनिया के अनौपचारिक सर्वश्रेष्ठ खिलाड़ी, 22 में शतरंज छोड़ दिया।", "दो रईस, अपने ही ओपेरा बॉक्स में हर चाल पर सलाह करते हुए।"],
    cold: "एक वज़ीर की कुर्बानी। बस दो मोहरे बचे। ऐसी मात जो आज भी पढ़ाई जाती है।",
    titleSeg: "मॉर्फ़ी बनाम दो रईस, पेरिस, 1858।",
    intro: "एक नौजवान अमेरिकी प्रतिभा, और सामने एक ड्यूक और एक काउंट जो मिलकर सोचते हैं।",
    ply1: "मॉर्फ़ी राजा के प्यादे से शुरू करते हैं, और रईस उसी तरह जवाब देते हैं।",
    ply7: "काला घोड़ा जल्दी पिन करता है, और सफ़ेद पिन को बदल देता है।",
    ply12: "काला अपना घोड़ा निकालता है।",
    km: "यहाँ काले के पास शांत रास्ता था: क्वीन d7 पर, और सफ़ेद का हमला देर से पहुँचता।",
    ply13: "क्वीन b3 पर f7 और b7 दोनों पर वार।",
    verdict: "मॉर्फ़ी ने लगभग बिना गलती खेला। विरोधी पास भी नहीं आए।",
    outro: "देखने के लिए शुक्रिया।",
    lineBlunder: "यह घोड़ा? सच में, भाई?",
    lineBrilliant: "ये हुई असली कुर्बानी।",
    label: "एक शांत रास्ता",
    chapters: ["शुरुआत", "हमला", "अंत"],
    thumb: "घोड़े की कुर्बानी",
    shortA: "वज़ीर b8 पर, शह! काले को लेना ही पड़ेगा।",
    shortB: "रुक d8 पर। मात। दो मोहरे ही काफ़ी थे।",
    lineMate: "बस दो मोहरे। इतना ही काफ़ी था।",
  },
} as const;

const SILENT = "audio/silent.mp3";
const segment = (lang: Lang, i: number, kind: VideoSpec["narration"][number]["kind"], ply: number | null, start_ms: number, duration_ms: number, text: string) => {
  const words = text.split(" ");
  const span = Math.floor((duration_ms * 0.9) / words.length);
  return {
    segment_id: `${lang}_seg-${String(i).padStart(3, "0")}`,
    kind,
    ply,
    text,
    audio: SILENT,
    start_ms,
    duration_ms,
    words: words.map((w, k) => ({ w, start_ms: start_ms + k * span, end_ms: start_ms + k * span + span - 20 })),
  };
};

const longForm = (lang: Lang): VideoSpec => {
  const t = T[lang];
  // Plies 1-12 play through the first Playback (1 s apart), 13-22 through the second (480 ms apart); the rest are
  // snapped to the verdict start, where nothing shows the board in motion.
  const showAt = (p: number) => (p <= 12 ? 14000 + (p - 1) * 1000 : p <= 22 ? 42000 + (p - 13) * 480 : 47000);
  const plies = base.plies.map((p) => ({
    ...p,
    show_at_ms: showAt(p.ply),
    class: p.ply === 12 ? ("blunder" as const) : p.ply === 19 ? ("brilliant" as const) : p.class === "best" ? ("good" as const) : p.class,
    eval: p.ply === 12 ? { cp: 420, mate: null } : p.eval,
  }));
  const narration = [
    segment(lang, 0, "cold_open", null, 0, 4900, t.cold),
    segment(lang, 1, "title", null, 5300, 2500, t.titleSeg),
    segment(lang, 2, "player_intro", null, 8100, 5000, t.intro),
    segment(lang, 3, "ply", 1, 13400, 6400, t.ply1),
    segment(lang, 4, "ply", 7, 20000, 4800, t.ply7),
    segment(lang, 5, "ply", 12, 25000, 1800, t.ply12),
    segment(lang, 6, "key_moment", 12, 27300, 14000, t.km),
    segment(lang, 7, "ply", 13, 42100, 4000, t.ply13),
    segment(lang, 8, "verdict", null, 47000, 5800, t.verdict),
    segment(lang, 9, "outro", null, 54200, 3000, t.outro),
  ];
  const mascot = { blunder: { pose: "faint" as const, line: t.lineBlunder }, brilliant: { pose: "slow_clap" as const, line: t.lineBrilliant } };
  return VideoSpec.parse({
    ...base,
    video_id: `cc-2026-0003-${lang}`,
    pair_id: "cc-2026-0003",
    language: lang,
    duration_ms: 60000,
    game: { ...base.game, white: { ...base.game.white, fact: t.facts[0] }, black: { ...base.game.black, fact: t.facts[1] } },
    plies,
    narration,
    beats: [
      { beat_id: "b-01", type: "blunder", ply: 12, at_ms: showAt(12), intensity: 3, mascot: mascot.blunder, fx: ["board_shake", "red_flash", "replay_move", "eval_whip"], sfx: "oof_01" },
      { beat_id: "b-02", type: "brilliant", ply: 19, at_ms: showAt(19), intensity: 2, mascot: mascot.brilliant, fx: ["gold_glint", "stamp_brilliant"], sfx: "ding_01" },
    ],
    chapters: [
      { title: t.chapters[0], start_ms: 0 },
      { title: t.chapters[1], start_ms: 20000 },
      { title: t.chapters[2], start_ms: 43000 },
    ],
    cold_open: { ply_from: 18, ply_to: 20, hook: t.hook },
    key_moments: [{ beat_id: "b-01", ply: 12, start_ms: 27000, duration_ms: 15000, label: t.label, line: ["d8d7", "b1c3", "g8f6", "c1g5"] }],
    verdict: { turning_point_ply: 12, accuracy: { white: 92, black: 61 } },
    thumbnail: { text: t.thumb, ply: 19, crop_origin: "a3", pose: "slow_clap" },
    youtube: { ...base.youtube, title: t.title, default_language: lang },
  });
};

const short = (lang: Lang, long: VideoSpec): VideoSpec => {
  const t = T[lang];
  const aDur = 4600;
  const startB = aDur + 300;
  const a = segment(lang, 0, "ply", 31, 0, aDur, t.shortA);
  const b = segment(lang, 1, "ply", 33, startB, 5000, t.shortB);
  const midWord = a.words[Math.floor(a.words.length / 2)].start_ms;
  const plies = base.plies.map((p) => ({ ...p, show_at_ms: p.ply <= 31 ? 0 : p.ply === 32 ? midWord : startB }));
  const mate = base.beats.find((x) => x.type === "checkmate")!;
  return VideoSpec.parse({
    ...long,
    video_id: `cc-2026-0004-${lang}`,
    pair_id: "cc-2026-0004",
    template: "shorts",
    format: { width: 1080, height: 1920, fps: 30 },
    duration_ms: startB + 5000,
    plies,
    narration: [a, b],
    beats: [{ ...mate, beat_id: "b-01", at_ms: startB, mascot: { pose: "mic_drop", line: t.lineMate } }],
    chapters: [{ title: t.chapters[2], start_ms: 0 }],
    cold_open: { ply_from: 31, ply_to: 33, hook: t.hook },
    key_moments: [],
    verdict: { turning_point_ply: 29, accuracy: { white: 92, black: 61 } },
    thumbnail: { text: t.thumb, ply: 31, crop_origin: "a5", pose: "mic_drop" },
  });
};

const write = (name: string, spec: VideoSpec) => {
  const dir = resolve(root, "spec/fixtures", name);
  mkdirSync(resolve(dir, "audio"), { recursive: true });
  mkdirSync(resolve(dir, "music"), { recursive: true });
  copyFileSync(resolve(fixtureDir, "audio/en_seg-000.mp3"), resolve(dir, SILENT));
  copyFileSync(resolve(fixtureDir, "music/bed_calm_01.mp3"), resolve(dir, "music/bed_calm_01.mp3"));
  writeFileSync(resolve(dir, "video_spec.json"), JSON.stringify(spec, null, 2) + "\n");
  console.log(`wrote ${name} (${spec.duration_ms} ms)`);
};

// The key-moment line must be legal from the position before ply 12 (lineStates throws naming the move otherwise).
lineStates(base.plies[10].fen_after, ["d8d7", "b1c3", "g8f6", "c1g5"]);
for (const lang of ["en", "hi"] as const) {
  const long = longForm(lang);
  write(`gallery-${lang}`, long);
  write(`gallery-short-${lang}`, short(lang, long));
}
