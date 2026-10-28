// The contract between Python and Remotion (docs/SPEC.md section 3).
// Edit only here; `npm run export-schema` regenerates spec/video_spec.schema.json.
// Cross-field rules marked "refine" are not expressible in JSON Schema, so the
// Python side enforces them separately (timeline / emit stages).
import { z } from "zod";

export const SUPPORTED_MAJOR = 1;

const ms = z.number().int().nonnegative();
const square = z.string().regex(/^[a-h][1-8]$/);
// Relative to the spec folder: no leading slash, drive letter or "..".
const relPath = z.string().regex(/^(?![/\\])(?![A-Za-z]:)(?!.*\.\.).+$/);

export const Language = z.enum(["en", "hi"]);
export const Template = z.enum(["studio", "shorts", "editorial", "arena"]);
export const Series = z.enum([
  "legendary_games",
  "indian_chess_heroes",
  "opening_explained",
  "blunder_hall_of_fame",
]);
export const BoardTheme = z.enum(["bone_slate", "walnut", "cool_grey", "warm_sand"]);

export const MoveClass = z.enum([
  "book",
  "best",
  "excellent",
  "good",
  "inaccuracy",
  "mistake",
  "blunder",
  "brilliant",
  "missed_win",
]);

export const BeatType = z.enum([
  "blunder",
  "mistake",
  "brilliant",
  "missed_win",
  "comeback",
  "long_think",
  "time_scramble",
  "king_walk",
  "promotion",
  "checkmate",
  "resign",
  "opening_exit",
]);

export const Pose = z.enum([
  "idle",
  "wave",
  "thinking",
  "side_eye",
  "facepalm",
  "faint",
  "slow_clap",
  "screaming",
  "shocked",
  "party",
  "checks_watch",
  "sweating",
  "binoculars",
  "jealous",
  "mic_drop",
  "bow",
  "point",
]);

// One id per effect in the section 8 beat table.
export const Fx = z.enum([
  "board_shake",
  "red_flash",
  "replay_move",
  "move_underline",
  "gold_glint",
  "stamp_brilliant",
  "ghost_arrow",
  "eval_whip",
  "clock_pulse",
  "clock_red",
  "king_trail",
  "crown_sparkle",
  "freeze_frame",
  "out_of_theory_label",
]);

export const NarrationKind = z.enum([
  "cold_open",
  "title",
  "player_intro",
  "ply",
  "chapter",
  "key_moment",
  "verdict",
  "outro",
]);

export const Player = z.object({
  name: z.string().min(1),
  // Historic games have no rating, title or federation; null, never omitted.
  rating: z.number().int().positive().nullable(),
  title: z.string().nullable(),
  country: z.string().length(2).nullable(),
  // 1.1.0: one short fact for the PlayerIntro card (spec section 5).
  fact: z.string().min(1).max(120),
});

// Exactly one of cp, mate is non-null; a union so JSON Schema enforces it too.
export const Eval = z.union([
  z.object({ cp: z.number().int(), mate: z.null() }),
  z.object({ cp: z.null(), mate: z.number().int() }),
]);

export const Arrow = z.object({
  from: square,
  to: square,
  color: z.enum(["best", "threat", "missed"]),
});

export const Highlight = z.object({ square, kind: z.enum(["last_move", "check"]) });

export const Ply = z.object({
  ply: z.number().int().positive(),
  san: z.string().min(1),
  uci: z.string().regex(/^[a-h][1-8][a-h][1-8][qrbn]?$/),
  fen_after: z.string().min(1),
  eval: Eval,
  best_uci: z.string().regex(/^[a-h][1-8][a-h][1-8][qrbn]?$/),
  class: MoveClass,
  clock_ms: ms.nullable(),
  show_at_ms: ms,
  arrows: z.array(Arrow).max(2),
  highlights: z.array(Highlight),
});

export const Word = z.object({ w: z.string().min(1), start_ms: ms, end_ms: ms });

export const NarrationSegment = z.object({
  segment_id: z.string().min(1),
  kind: NarrationKind,
  ply: z.number().int().positive().nullable(),
  text: z.string().min(1),
  audio: relPath,
  start_ms: ms,
  duration_ms: z.number().int().positive(),
  words: z.array(Word).min(1),
});

export const Beat = z.object({
  beat_id: z.string().min(1),
  type: BeatType,
  ply: z.number().int().positive(),
  at_ms: ms,
  intensity: z.number().int().min(1).max(3),
  mascot: z.object({ pose: Pose, line: z.string().min(1) }),
  fx: z.array(Fx),
  sfx: z.string().nullable(),
});

const uci = z.string().regex(/^[a-h][1-8][a-h][1-8][qrbn]?$/);

// 1.1.0 scene data (Gate A finding: scenes in spec section 5 had no data to draw from).
export const ColdOpen = z.object({
  // Board shows the position before ply_from, then plays ply_from..ply_to.
  ply_from: z.number().int().positive(),
  ply_to: z.number().int().positive(),
  hook: z.string().min(1).max(60),
});

export const KeyMoment = z.object({
  beat_id: z.string().min(1),
  ply: z.number().int().positive(),
  start_ms: ms,
  duration_ms: z.number().int().positive(),
  label: z.string().min(1).max(40),
  // The alternative the narration discusses, as UCI moves from the position before `ply`.
  line: z.array(uci).min(1).max(8),
});

export const Verdict = z.object({
  turning_point_ply: z.number().int().positive(),
  // Lichess-style accuracy per side, 0-100.
  accuracy: z.object({ white: z.number().min(0).max(100), black: z.number().min(0).max(100) }),
});

export const Thumbnail = z.object({
  // At most 4 words (spec section 6); never the title verbatim.
  text: z.string().regex(/^\S+(?: \S+){0,3}$/),
  ply: z.number().int().positive(),
  // Lower-left square of the 4x4 crop, from White's view.
  crop_origin: z.string().regex(/^[a-e][1-5]$/),
  pose: Pose,
});

export const VideoSpec = z
  .object({
    spec_version: z.string().regex(new RegExp(`^${SUPPORTED_MAJOR}\\.\\d+\\.\\d+$`)),
    video_id: z.string().regex(/^cc-\d{4}-\d{4}-(en|hi)$/),
    pair_id: z.string().regex(/^cc-\d{4}-\d{4}$/),
    language: Language,
    template: Template,
    series: Series,
    board: z.object({ orientation: z.enum(["white", "black"]), theme: BoardTheme }),
    format: z.object({
      width: z.number().int().positive(),
      height: z.number().int().positive(),
      fps: z.number().int().positive(),
    }),
    duration_ms: z.number().int().positive(),
    game: z.object({
      source: z.enum(["lichess", "local"]),
      source_id: z.string().min(1),
      white: Player,
      black: Player,
      event: z.string().min(1),
      date: z.string().min(1),
      result: z.enum(["1-0", "0-1", "1/2-1/2"]),
      eco: z.string().regex(/^[A-E]\d{2}$/),
      opening: z.string().min(1),
      pgn: z.string().min(1),
    }),
    plies: z.array(Ply).min(1),
    narration: z.array(NarrationSegment).min(1),
    beats: z.array(Beat),
    chapters: z.array(z.object({ title: z.string().min(1), start_ms: ms })).min(1),
    cold_open: ColdOpen,
    key_moments: z.array(KeyMoment),
    verdict: Verdict,
    thumbnail: Thumbnail,
    music: z.object({
      track: relPath,
      volume: z.number().min(0).max(1),
      duck_under_voice: z.number().min(0).max(1),
    }),
    youtube: z.object({
      title: z.string().min(1).max(100),
      description: z.string().min(1).max(5000),
      tags: z.array(z.string()),
      playlist: z.string().min(1),
      publish_at: z.iso.datetime(),
      default_language: Language,
      made_for_kids: z.literal(false),
      contains_synthetic_media: z.boolean(),
      thumbnail: relPath,
    }),
  })
  .superRefine((s, ctx) => {
    // refine: video_id carries the pair_id and language.
    if (s.video_id !== `${s.pair_id}-${s.language}`) {
      ctx.addIssue({ code: "custom", path: ["video_id"], message: "must equal `${pair_id}-${language}`" });
    }
    // refine: template-specific format (section 3).
    if (s.template === "shorts") {
      if (s.format.width !== 1080 || s.format.height !== 1920) {
        ctx.addIssue({ code: "custom", path: ["format"], message: "shorts must be 1080x1920" });
      }
      if (s.duration_ms > 175000) {
        ctx.addIssue({ code: "custom", path: ["duration_ms"], message: "shorts must be <= 175000 ms" });
      }
    }
    // refine: narration ordered and non-overlapping.
    s.narration.forEach((seg, i) => {
      const prev = s.narration[i - 1];
      if (prev && seg.start_ms < prev.start_ms + prev.duration_ms) {
        ctx.addIssue({ code: "custom", path: ["narration", i, "start_ms"], message: "overlaps previous segment" });
      }
    });
    // refine: scene plies exist and cold open runs forward.
    const n = s.plies.length;
    const plyOk = (p: number) => p >= 1 && p <= n;
    if (!plyOk(s.cold_open.ply_from) || !plyOk(s.cold_open.ply_to) || s.cold_open.ply_from > s.cold_open.ply_to) {
      ctx.addIssue({ code: "custom", path: ["cold_open"], message: "ply_from..ply_to must be a forward range of existing plies" });
    }
    s.key_moments.forEach((k, i) => {
      if (!plyOk(k.ply)) ctx.addIssue({ code: "custom", path: ["key_moments", i, "ply"], message: "no such ply" });
      if (!s.beats.some((b) => b.beat_id === k.beat_id)) {
        ctx.addIssue({ code: "custom", path: ["key_moments", i, "beat_id"], message: "must reference a beat" });
      }
    });
    if (!plyOk(s.verdict.turning_point_ply)) ctx.addIssue({ code: "custom", path: ["verdict", "turning_point_ply"], message: "no such ply" });
    if (!plyOk(s.thumbnail.ply)) ctx.addIssue({ code: "custom", path: ["thumbnail", "ply"], message: "no such ply" });
    if (s.thumbnail.text.toLowerCase() === s.youtube.title.toLowerCase()) {
      ctx.addIssue({ code: "custom", path: ["thumbnail", "text"], message: "must not repeat the title" });
    }
    // refine: plies numbered 1..n in order.
    s.plies.forEach((p, i) => {
      if (p.ply !== i + 1) {
        ctx.addIssue({ code: "custom", path: ["plies", i, "ply"], message: `expected ply ${i + 1}` });
      }
    });
  });

export type VideoSpec = z.infer<typeof VideoSpec>;
export type KeyMoment = z.infer<typeof KeyMoment>;
export type Ply = z.infer<typeof Ply>;
export type Beat = z.infer<typeof Beat>;
export type NarrationSegment = z.infer<typeof NarrationSegment>;
