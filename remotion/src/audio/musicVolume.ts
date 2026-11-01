import type { NarrationSegment, VideoSpec } from "../spec/schema";

export const DUCK_RAMP_MS = 200;
const clamp01 = (n: number): number => Math.min(1, Math.max(0, n));

/**
 * Music gain at `ms`: `volume` in silence, `duck_under_voice` while any narration plays, with 200 ms ramps
 * (the dip finishes as the voice starts; the recovery starts when it ends).
 */
export const musicVolume = (ms: number, narration: Pick<NarrationSegment, "start_ms" | "duration_ms">[], music: VideoSpec["music"]): number => {
  let ducked = 0;
  for (const s of narration) {
    const down = clamp01((ms - (s.start_ms - DUCK_RAMP_MS)) / DUCK_RAMP_MS);
    const up = clamp01((s.start_ms + s.duration_ms + DUCK_RAMP_MS - ms) / DUCK_RAMP_MS);
    ducked = Math.max(ducked, Math.min(down, up));
  }
  return music.volume + (music.duck_under_voice - music.volume) * ducked;
};
