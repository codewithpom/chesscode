import { Audio } from "@remotion/media";
import type { FC } from "react";
import { Sequence, useVideoConfig } from "remotion";
import dingSrc from "../assets/sfx/ding_01.mp3";
import gaspSrc from "../assets/sfx/gasp_01.mp3";
import hmmSrc from "../assets/sfx/hmm_01.mp3";
import oofSrc from "../assets/sfx/oof_01.mp3";
import sparkleSrc from "../assets/sfx/sparkle_01.mp3";
import sting1Src from "../assets/sfx/sting_01.mp3";
import sting2Src from "../assets/sfx/sting_02.mp3";
import tick1Src from "../assets/sfx/tick_01.mp3";
import tick2Src from "../assets/sfx/tick_02.mp3";
import whipSrc from "../assets/sfx/whip_01.mp3";
import type { Beat } from "../spec/schema";
import { msToFrame } from "../spec/time";

// Ids from config/beats.yaml `sfx`. Peaks are <= -12 dBFS in the files and the gain is 0.5 on top, so a sound
// is always quieter than the narration at volume 1.
const SRC: Record<string, string> = {
  oof_01: oofSrc,
  hmm_01: hmmSrc,
  ding_01: dingSrc,
  gasp_01: gaspSrc,
  whip_01: whipSrc,
  tick_01: tick1Src,
  tick_02: tick2Src,
  sparkle_01: sparkleSrc,
  sting_01: sting1Src,
  sting_02: sting2Src,
};
export const SFX_GAIN = 0.5;
export const sfxIds = Object.keys(SRC);

/** One sound per beat with a non-null `sfx`, at `at_ms`. An id without a file is skipped, never an error. */
export const Sfx: FC<{ beats: Beat[] }> = ({ beats }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {beats.map((b) =>
        b.sfx && SRC[b.sfx] ? (
          <Sequence key={b.beat_id} from={msToFrame(b.at_ms, fps)} layout="none">
            <Audio src={SRC[b.sfx]} volume={SFX_GAIN} />
          </Sequence>
        ) : null,
      )}
    </>
  );
};
