import { Composition } from "remotion";
import { calculateGalleryMetadata, CoreGallery, GalleryProps } from "./compositions/CoreGallery";
import fixture from "../../spec/fixtures/cc-2026-0001-en/video_spec.json";
import shortFixture from "../../spec/fixtures/cc-2026-0002-en/video_spec.json";
import { calculateShortsMetadata, ShortsVideo } from "./compositions/ShortsVideo";
import { calculateStudioMetadata, StudioVideo } from "./compositions/StudioVideo";
import { calculateThumbnailMetadata, Thumbnail } from "./compositions/Thumbnail";
import { VideoSpec } from "./spec/schema";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="StudioVideo"
      component={StudioVideo}
      schema={VideoSpec}
      defaultProps={VideoSpec.parse(fixture)}
      calculateMetadata={calculateStudioMetadata}
      // Overridden by calculateMetadata from the spec's format and duration_ms.
      durationInFrames={1}
      fps={30}
      width={1920}
      height={1080}
    />
    <Composition
      id="ShortsVideo"
      component={ShortsVideo}
      schema={VideoSpec}
      defaultProps={VideoSpec.parse(shortFixture)}
      calculateMetadata={calculateShortsMetadata}
      durationInFrames={1}
      fps={30}
      width={1080}
      height={1920}
    />
    {/* Rendered with `remotion still Thumbnail`: one frame, 1280 x 720. */}
    <Composition
      id="Thumbnail"
      component={Thumbnail}
      schema={VideoSpec}
      defaultProps={VideoSpec.parse(fixture)}
      calculateMetadata={calculateThumbnailMetadata}
      durationInFrames={1}
      fps={30}
      width={1280}
      height={720}
    />
    {/* Rendered with `remotion still`; a Composition (not Still) so fps is 30, which the board timing needs. */}
    <Composition
      id="CoreGallery"
      component={CoreGallery}
      schema={GalleryProps}
      defaultProps={{ panel: "board-bone_slate" as const }}
      calculateMetadata={calculateGalleryMetadata}
      durationInFrames={1}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
