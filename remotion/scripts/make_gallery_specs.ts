// Synthetic specs for the TemplateGallery and the 60 s Studio clip (Task 8), derived from the Opera Game fixture:
//   npx tsx scripts/make_gallery_specs.ts
// writes spec/fixtures/gallery-{en,hi}/ (60 s long-form: cold open, title, player intro, playback with a faint-worthy
// blunder and a brilliant beat, one key moment, verdict, outro) and gallery-short-{en,hi}/ (the mate finish as a Short).
// English narration is the real ElevenLabs bake-off voice (build/bakeoff/elevenlabs_en.mp3, George, -14.5 LUFS), cut
// at word boundaries into the ten segments; Hindi and the Shorts use the fixture's silent MP3. Every spec is validated by the Zod schema before it is written. The Hindi is
// written for layout review (Devanagari at real sizes); the owner should review the wording before anything ships.
import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
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

type Word = { w: string; start_ms: number; end_ms: number };
const ffmpegExe = (): string =>
  execFileSync("python", ["-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"], { encoding: "utf8" }).trim();

/**
 * Cuts the real narration into one slice per window: whole sentences while they fit (a pad of 80 ms before and
 * 120 ms after), else as many whole words as fit. Words keep their timing relative to the slice start.
 */
const realVoice = (maxima: number[], dir: string): { audio: string; durationMs: number; words: Word[] }[] => {
  const bakeoff = process.env.BAKEOFF_DIR ?? resolve(root, "build/bakeoff"); // the bake-off output is git-ignored; point BAKEOFF_DIR at it
  const src = resolve(bakeoff, "elevenlabs_en.mp3");
  if (!existsSync(src)) throw new Error(`real narration not found: ${src}`);
  const words: Word[] = JSON.parse(readFileSync(resolve(bakeoff, "elevenlabs_en.words.json"), "utf8"));
  mkdirSync(resolve(dir, "audio"), { recursive: true });
  mkdirSync(resolve(dir, "narration"), { recursive: true });
  copyFileSync(resolve(bakeoff, "elevenlabs_en.words.json"), resolve(dir, "narration/elevenlabs_en.words.json"));
  const sentences: Word[][] = [];
  let cur: Word[] = [];
  for (const w of words) {
    cur.push(w);
    if (/[.?!]$/.test(w.w)) {
      sentences.push(cur);
      cur = [];
    }
  }
  if (cur.length) sentences.push(cur);
  const PAD_BEFORE = 80;
  const PAD_AFTER = 120;
  const out: { audio: string; durationMs: number; words: Word[] }[] = [];
  let next = 0; // next unused sentence
  maxima.forEach((max, i) => {
    let take: Word[] = [];
    while (next < sentences.length) {
      const trial = [...take, ...sentences[next]];
      if (trial[trial.length - 1].end_ms - trial[0].start_ms + PAD_BEFORE + PAD_AFTER > max) break;
      take = trial;
      next++;
    }
    if (take.length === 0) {
      // No whole sentence fits: whole words of the next one.
      const s0 = sentences[next];
      for (const w of s0) {
        const trial = [...take, w];
        if (trial[trial.length - 1].end_ms - trial[0].start_ms + PAD_BEFORE + PAD_AFTER > max) break;
        take = trial;
      }
      sentences[next] = s0.slice(take.length);
      if (sentences[next].length === 0) next++;
    }
    const startMs = Math.max(0, take[0].start_ms - PAD_BEFORE);
    const durationMs = take[take.length - 1].end_ms + PAD_AFTER - startMs;
    const audio = `audio/en_seg-${String(i).padStart(3, "0")}.mp3`;
    execFileSync(ffmpegExe(), ["-hide_banner", "-loglevel", "error", "-y", "-ss", String(startMs / 1000), "-t", String(durationMs / 1000), "-i", src, "-c:a", "libmp3lame", "-b:a", "128k", resolve(dir, audio)]);
    out.push({ audio, durationMs, words: take.map((w) => ({ w: w.w, start_ms: w.start_ms - startMs, end_ms: w.end_ms - startMs })) });
  });
  return out;
};

const longForm = (lang: Lang): VideoSpec => {
  const t = T[lang];
  // Plies 1-12 play through the first Playback (1 s apart), 13-19 through the second (480 ms apart); after the
  // brilliant ply 19 the board holds 1.2 s for the reaction (docs/SPEC.md section 8: the pipeline leaves a gap),
  // then plies 20-22 follow 320 ms apart. The rest snap to the verdict start, where the board is not in motion.
  const showAt = (p: number) => (p <= 12 ? 14000 + (p - 1) * 1000 : p <= 19 ? 42000 + (p - 13) * 480 : p <= 22 ? 46080 + (p - 20) * 320 : 47000);
  const plies = base.plies.map((p) => ({
    ...p,
    show_at_ms: showAt(p.ply),
    class: p.ply === 12 ? ("blunder" as const) : p.ply === 19 ? ("brilliant" as const) : p.class === "best" ? ("good" as const) : p.class,
    eval: p.ply === 12 ? { cp: 420, mate: null } : p.eval,
  }));
  // Scene windows (start, longest narration that fits before the next scene or segment starts).
  const windows = [
    { kind: "cold_open", ply: null, start: 0, max: 5800, text: t.cold },
    { kind: "title", ply: null, start: 6000, max: 2700, text: t.titleSeg },
    { kind: "player_intro", ply: null, start: 8800, max: 5100, text: t.intro },
    { kind: "ply", ply: 1, start: 14000, max: 5900, text: t.ply1 },
    { kind: "ply", ply: 7, start: 20000, max: 4900, text: t.ply7 },
    { kind: "ply", ply: 12, start: 25000, max: 2200, text: t.ply12 },
    { kind: "key_moment", ply: 12, start: 27300, max: 14700, text: t.km },
    { kind: "ply", ply: 13, start: 42100, max: 4800, text: t.ply13 },
    { kind: "verdict", ply: null, start: 47000, max: 7100, text: t.verdict },
    { kind: "outro", ply: null, start: 54200, max: 5700, text: t.outro },
  ] as const;
  const dir = resolve(root, "spec/fixtures", `gallery-${lang}`);
  const voice = lang === "en" ? realVoice(windows.map((w) => w.max), dir) : null;
  const narration = windows.map((w, i) => {
    if (voice) {
      const v = voice[i];
      return {
        segment_id: `${lang}_seg-${String(i).padStart(3, "0")}`,
        kind: w.kind,
        ply: w.ply,
        text: v.words.map((x) => x.w).join(" "),
        audio: v.audio,
        start_ms: w.start,
        duration_ms: v.durationMs,
        words: v.words.map((x) => ({ w: x.w, start_ms: w.start + x.start_ms, end_ms: w.start + x.end_ms })),
      };
    }
    return segment(lang, i, w.kind, w.ply, w.start, Math.min(w.max - 300, w.kind === "key_moment" ? 14000 : w.kind === "ply" && w.ply === 12 ? 1800 : 5000), w.text);
  });
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
