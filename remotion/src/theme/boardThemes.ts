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

// Black pieces: rhosgfx shapes (CC0) recolored in src/assets/pieces/b?.svg, see public/CREDITS.md.
export const pieceBlack = "#2E323B";
export const pieceBlackInk = "#D9DCE1";

const check = "#E5484D";

export const boardThemes: Record<z.infer<typeof BoardTheme>, BoardPalette> = {
  bone_slate: { light: "#E8E2D4", dark: "#6E7F86", lastMoveLight: "#DCD3B0", lastMoveDark: "#8E9A8C", check },
  // Four hue families by dark-square hue: slate 198, walnut 26, sage 85, dusty rose 342 degrees.
  // The enum keys are fixed by the spec schema: cool_grey is now sage green, warm_sand is dusty rose.
  walnut: { light: "#EEE0C8", dark: "#9C7658", lastMoveLight: "#E0D1A8", lastMoveDark: "#AC946E", check },
  cool_grey: { light: "#F0EEDD", dark: "#7B8967", lastMoveLight: "#E1DAB6", lastMoveDark: "#96A078", check },
  warm_sand: { light: "#F6EEEC", dark: "#A57C88", lastMoveLight: "#E5DAC0", lastMoveDark: "#B2988D", check },
};
