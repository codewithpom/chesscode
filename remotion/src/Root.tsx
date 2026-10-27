import { Composition } from "remotion";
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
  </>
);
