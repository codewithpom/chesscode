import { Easing, type SpringConfig } from "remotion";

// One enter easing, one exit easing, one UI spring for the whole channel (docs/SPEC.md section 6).
export const motion = {
  enter: Easing.bezier(0.22, 1, 0.36, 1),
  exit: Easing.bezier(0.4, 0, 1, 1),
  // Overdamped (damping > 2*sqrt(stiffness*mass)): settles without overshoot.
  uiSpring: { damping: 28, mass: 1, stiffness: 170, overshootClamping: false } satisfies SpringConfig,
  pieceMoveMs: 280,
  captureFadeMs: 120,
  uiEnterMs: 300,
  staggerMs: 60,
} as const;

export const uiSpring: SpringConfig = motion.uiSpring;
