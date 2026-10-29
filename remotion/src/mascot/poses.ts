import type { z } from "zod";
import type { Pose } from "../spec/schema";
import type { PoseState } from "./poseState";

const BASE: PoseState = {
  squash: 1, lean: 0, headTilt: 0, eyeOpen: 1, pupilX: 0, pupilY: 0, eyeScale: 1,
  browAngle: 0, browY: 0, browRY: 0, mouth: "smile", armL: 0, armR: 0, arms: "none",
  prop: "crown", propLift: 0, offsetX: 0, offsetY: 0, sweat: 0,
};
const p = (o: Partial<PoseState>): PoseState => ({ ...BASE, ...o });

// The six poses on the approved sheet (neutral=idle, side_eye, facepalm, shocked, slow_clap, sweating)
// map field-for-field from `Face`. The other eleven are composed from the same vocabulary.
export const POSES: Record<z.infer<typeof Pose>, PoseState> = {
  idle: p({}),
  wave: p({ arms: "up", headTilt: 3, eyeOpen: 0.9 }),
  thinking: p({ arms: "chin", pupilX: 0.4, pupilY: -0.8, browAngle: 0.25, browY: 0.3, browRY: 0.5, mouth: "flat", headTilt: -6 }),
  side_eye: p({ eyeOpen: 0.5, pupilX: 1, browAngle: 0.6, browY: -0.4, browRY: 1.2, mouth: "flat" }),
  facepalm: p({ eyeOpen: 0, browAngle: -0.8, browY: 0.4, mouth: "frown", arms: "face", lean: -4 }),
  // Out position: tipped over to the right and below the frame (520 rig units = past the bottom of both boxes).
  faint: p({ eyeOpen: 0, browAngle: -0.8, mouth: "o", lean: 90, offsetX: 60, offsetY: 520 }),
  slow_clap: p({ eyeOpen: 0.7, pupilY: -0.4, browAngle: -0.3, browY: 0.4, mouth: "smirk", arms: "clap" }),
  screaming: p({ eyeScale: 1.15, browAngle: -0.9, browY: 1, mouth: "wide", squash: 0.94 }),
  shocked: p({ eyeScale: 1.18, browY: 1, mouth: "o", lean: 3, propLift: 14 }),
  party: p({ eyeOpen: 0.8, browY: 0.5, arms: "up", prop: "party_hat", headTilt: -4 }),
  checks_watch: p({ eyeOpen: 0.75, pupilY: 0.7, browAngle: 0.2, mouth: "flat", arms: "wrist", prop: "watch", headTilt: 4 }),
  sweating: p({ eyeScale: 1.12, pupilX: -0.5, browAngle: -0.9, browY: 0.5, mouth: "flat", sweat: 0.4 }),
  binoculars: p({ eyeOpen: 0, arms: "hold", prop: "binoculars", mouth: "flat" }),
  jealous: p({ pupilX: 0.7, pupilY: 0.3, browAngle: 0.8, browY: -0.3, mouth: "frown", arms: "hold", lean: -2 }),
  mic_drop: p({ eyeOpen: 0.7, browAngle: 0.2, mouth: "smirk", arms: "up", prop: "mic", propLift: -147, lean: 2 }),
  bow: p({ eyeOpen: 0, squash: 1.1, offsetY: 6, headTilt: 0, mouth: "smile" }),
  point: p({ pupilX: 1, browY: 0.5, arms: "point", headTilt: 4 }),
};
