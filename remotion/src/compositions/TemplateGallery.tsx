// Review stills of the templates (docs/SPEC.md section 5/6): one still per Studio scene type in English and Hindi,
// the Shorts hook and beat frames, and the thumbnail. Each panel draws the real composition at a chosen moment of a
// synthetic spec (scripts/make_gallery_specs.ts); no audio is mounted.
//   npx remotion still TemplateGallery build/m5/gallery/<panel>.png --props='{"panel":"playback-en"}'
import type { FC } from "react";
import { CalculateMetadataFunction, Sequence } from "remotion";
import { z } from "zod";
import longEn from "../../../spec/fixtures/gallery-en/video_spec.json";
import longHi from "../../../spec/fixtures/gallery-hi/video_spec.json";
import shortEn from "../../../spec/fixtures/gallery-short-en/video_spec.json";
import shortHi from "../../../spec/fixtures/gallery-short-hi/video_spec.json";
import { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { ShortsVisuals } from "./ShortsVideo";
import { StudioVisuals } from "./StudioVideo";
import { THUMB, Thumbnail } from "./Thumbnail";

export const GALLERY_SPECS = {
  en: VideoSpec.parse(longEn),
  hi: VideoSpec.parse(longHi),
  "short-en": VideoSpec.parse(shortEn),
  "short-hi": VideoSpec.parse(shortHi),
} as const;

type Lang = "en" | "hi";
type Panel = { spec: keyof typeof GALLERY_SPECS; kind: "studio" | "shorts" | "thumbnail"; ms: number; scene?: string };

const studio = (lang: Lang, scene: string, ms: number): Panel => ({ spec: lang, kind: "studio", ms, scene });
// Moments of the 60 s spec: cold open 0-5.3 s (its mate reaction at about 2.2 s), title 5.3-8.1, intro 8.1-13.4,
// playback to 27 s (the blunder at 25 s, Pyaada falling), key moment 27-42, playback to 47 (brilliant at 44.9 s),
// verdict 47-54, outro 54-60 (waves at 54.4 s, points from 57.6 s).
const at = (lang: Lang): Record<string, Panel> => ({
  [`cold_open-${lang}`]: studio(lang, "cold_open", 2700),
  [`title-${lang}`]: studio(lang, "title", 6600),
  [`player_intro-${lang}`]: studio(lang, "player_intro", 10500),
  [`playback-${lang}`]: studio(lang, "playback", 45600),
  [`playback_blunder-${lang}`]: studio(lang, "playback", 25400),
  [`key_moment-${lang}`]: studio(lang, "key_moment", 33000),
  [`verdict-${lang}`]: studio(lang, "verdict", 50000),
  [`outro-${lang}`]: studio(lang, "outro", 58800),
  [`shorts_hook-${lang}`]: { spec: `short-${lang}`, kind: "shorts", ms: 500 },
  [`shorts_beat-${lang}`]: { spec: `short-${lang}`, kind: "shorts", ms: 5900 },
  [`thumbnail-${lang}`]: { spec: lang, kind: "thumbnail", ms: 0 },
});
export const PANEL_TABLE: Record<string, Panel> = { ...at("en"), ...at("hi") };
export const PANELS = Object.keys(PANEL_TABLE) as [string, ...string[]];

export const GalleryProps = z.object({ panel: z.enum(PANELS) });
export type GalleryProps = z.infer<typeof GalleryProps>;

export const calculateGalleryPanelMetadata: CalculateMetadataFunction<GalleryProps> = ({ props }) => {
  const p = PANEL_TABLE[props.panel];
  const spec = GALLERY_SPECS[p.spec];
  // The composition keeps the spec's own length so reactions and the Shorts loop see their real duration.
  if (p.kind === "thumbnail") return { width: THUMB.width, height: THUMB.height, durationInFrames: 1, fps: 30 };
  return { width: spec.format.width, height: spec.format.height, durationInFrames: msToFrame(spec.duration_ms, 30), fps: 30 };
};

export const TemplateGallery: FC<GalleryProps> = ({ panel }) => {
  const p = PANEL_TABLE[panel];
  const spec = GALLERY_SPECS[p.spec];
  if (p.kind === "thumbnail") return <Thumbnail {...spec} />;
  // The still is frame 0; shifting the timeline back puts the compositions at the chosen moment.
  return (
    <Sequence from={-msToFrame(p.ms, 30)} layout="none">
      {p.kind === "studio" ? <StudioVisuals {...spec} /> : <ShortsVisuals {...spec} />}
    </Sequence>
  );
};
