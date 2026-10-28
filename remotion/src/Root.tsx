import { Composition } from "remotion";
import { calculateGalleryMetadata, CoreGallery, GalleryProps } from "./compositions/CoreGallery";
import fixture from "../../spec/fixtures/cc-2026-0001-en/video_spec.json";
import { calculateStudioMetadata, StudioVideo } from "./compositions/StudioVideo";
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
