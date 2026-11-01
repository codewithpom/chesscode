import type { KeyMoment, VideoSpec } from "../spec/schema";

export type SceneKind = "cold_open" | "title" | "player_intro" | "playback" | "key_moment" | "verdict" | "outro";
export type SceneRange = { kind: SceneKind; startMs: number; endMs: number; keyMoment?: KeyMoment };

// Narration kinds that own a whole scene. `ply` and `chapter` narrate Playback; `key_moment`
// narration sits inside the range that spec.key_moments[] already gives.
const OWN_SCENE = new Set<SceneKind>(["cold_open", "title", "player_intro", "verdict", "outro"]);

/**
 * Cuts the spec into contiguous scene ranges covering 0..duration_ms.
 * A scene runs from its narration segment's start to the next segment's start (outro: to duration_ms);
 * key_moments[] cut their own ranges; Playback fills every gap; an outro is added after the last
 * narration when the script has no outro segment. A key moment keeps its exact ms (it cuts what it
 * overlaps); any other scene is clipped to start after the previous one; empty ranges are dropped.
 */
export const sceneRanges = (spec: VideoSpec): SceneRange[] => {
  const total = spec.duration_ms;
  const raw: SceneRange[] = [];
  spec.narration.forEach((n, i) => {
    const kind = n.kind as SceneKind;
    if (!OWN_SCENE.has(kind)) return;
    const next = spec.narration[i + 1];
    const endMs = kind === "outro" ? total : next ? next.start_ms : n.start_ms + n.duration_ms;
    raw.push({ kind, startMs: n.start_ms, endMs });
  });
  for (const keyMoment of spec.key_moments)
    raw.push({ kind: "key_moment", startMs: keyMoment.start_ms, endMs: keyMoment.start_ms + keyMoment.duration_ms, keyMoment });
  if (!raw.some((r) => r.kind === "outro")) {
    const lastEnd = Math.max(...spec.narration.map((n) => n.start_ms + n.duration_ms));
    if (lastEnd < total) raw.push({ kind: "outro", startMs: lastEnd, endMs: total });
  }
  raw.sort((a, b) => a.startMs - b.startMs);

  const out: SceneRange[] = [];
  const cursor = () => (out.length ? out[out.length - 1].endMs : 0);
  for (const r0 of raw) {
    const r = { ...r0, endMs: Math.min(r0.endMs, total) };
    if (r.kind === "key_moment" && out.length && cursor() > r.startMs) {
      out[out.length - 1].endMs = r.startMs;
      if (out[out.length - 1].endMs <= out[out.length - 1].startMs) out.pop();
    }
    r.startMs = Math.max(r.startMs, cursor());
    if (r.endMs <= r.startMs) continue;
    if (r.startMs > cursor()) out.push({ kind: "playback", startMs: cursor(), endMs: r.startMs });
    out.push(r);
  }
  if (cursor() < total) out.push({ kind: "playback", startMs: cursor(), endMs: total });
  return out;
};

/** Chapter cards: every chapter after the first that starts inside Playback (other scenes carry their own title). */
export const chapterCardsFor = (spec: VideoSpec): { title: string; startMs: number }[] => {
  const playback = sceneRanges(spec).filter((r) => r.kind === "playback");
  return spec.chapters
    .slice(1)
    .filter((c) => playback.some((r) => c.start_ms >= r.startMs && c.start_ms < r.endMs))
    .map((c) => ({ title: c.title, startMs: c.start_ms }));
};
