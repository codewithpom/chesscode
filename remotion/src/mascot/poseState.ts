// A pose is a target PoseState of plain numbers (docs/SPEC.md section 7). Field units follow the
// approved sheet (design/mascot/build_sheets.py `Face`): browAngle/browY/browRY are sheet units
// (-1..1), scaled to degrees / px when drawn; offsets and lifts are rig units (rig box is 240 x 260).
export type MouthId = "smile" | "flat" | "o" | "wide" | "frown" | "smirk" | "open_talk" | "wobble";
export type ArmsId = "none" | "chin" | "face" | "clap" | "up" | "wrist" | "point" | "hold";
export type PropId = "crown" | "party_hat" | "mic" | "binoculars" | "watch" | "none";

export type PoseState = {
  /** > 1 = squashed: scaleX = squash, scaleY = 1 / squash (volume conserved). */
  squash: number;
  /** Body rotation about the base, degrees. */
  lean: number;
  /** Head rotation about the neck, degrees. */
  headTilt: number;
  /** 0 = shut, 1 = open. */
  eyeOpen: number;
  pupilX: number;
  pupilY: number;
  eyeScale: number;
  /** + = angry (inner ends down), - = worried. */
  browAngle: number;
  /** + = raised. */
  browY: number;
  /** Extra raise of the right brow only (skeptical look). */
  browRY: number;
  mouth: MouthId;
  /** Swing of each arm about its shoulder, degrees, on top of the `arms` preset. */
  armL: number;
  armR: number;
  arms: ArmsId;
  prop: PropId;
  /** Vertical lift of the prop in rig units (+ = up). */
  propLift: number;
  offsetX: number;
  offsetY: number;
  /** 0 = no drop; (0,1] = progress of one sweat drop. */
  sweat: number;
};

export const scaleOf = (squash: number): { x: number; y: number } => ({ x: squash, y: 1 / squash });

const ID_KEYS = ["mouth", "arms", "prop"] as const;

export const lerpPose = (a: PoseState, b: PoseState, t: number): PoseState => {
  const out = { ...a } as Record<string, number | string>;
  for (const k of Object.keys(a) as (keyof PoseState)[]) {
    if ((ID_KEYS as readonly string[]).includes(k)) out[k] = t >= 0.5 ? b[k] : a[k];
    else out[k] = (a[k] as number) + ((b[k] as number) - (a[k] as number)) * t;
  }
  return out as PoseState;
};
