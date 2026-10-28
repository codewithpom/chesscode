import type { z } from "zod";
import type { BoardTheme } from "../spec/schema";

// lastMoveLight / lastMoveDark: opaque tints of the square colors for the last-move squares
// (square mixed 35% toward olive #C6B66D on light squares, #C9CC97 on dark; bone_slate values are the
// design-critic's, the other themes are derived the same way). No amber, no semantic colors.
export type BoardPalette = {
  light: string;
  dark: string;
  lastMoveLight: string;
  lastMoveDark: string;
  check: string;
};

const check = "#E5484D";

export const boardThemes: Record<z.infer<typeof BoardTheme>, BoardPalette> = {
  bone_slate: { light: "#E8E2D4", dark: "#6E7F86", lastMoveLight: "#DCD3B0", lastMoveDark: "#8E9A8C", check },
  // walnut, cool_grey, warm_sand: builder choices, flagged for design review.
  walnut: { light: "#EEE0C8", dark: "#9C7658", lastMoveLight: "#E0D1A8", lastMoveDark: "#AC946E", check },
  cool_grey: { light: "#EAEDF0", dark: "#7C8796", lastMoveLight: "#DDDAC2", lastMoveDark: "#979F96", check },
  warm_sand: { light: "#F3EAD6", dark: "#A58B5E", lastMoveLight: "#E3D8B1", lastMoveDark: "#B2A272", check },
};
