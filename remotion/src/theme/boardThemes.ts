import type { z } from "zod";
import type { BoardTheme } from "../spec/schema";

export type BoardPalette = { light: string; dark: string; coord: string; lastMove: string; check: string };

// coord is near-black so one color reads on both square colors (>= 4.5:1, tested).
// lastMove is a translucent flat tint laid over either square color.
const coord = "#0F1115";
const check = "#E5484D";

export const boardThemes: Record<z.infer<typeof BoardTheme>, BoardPalette> = {
  bone_slate: { light: "#E8E2D4", dark: "#6E7F86", coord, lastMove: "rgba(242,169,59,0.38)", check },
  // walnut, cool_grey, warm_sand: builder choices, flagged for design review.
  walnut: { light: "#EEE0C8", dark: "#9C7658", coord, lastMove: "rgba(242,169,59,0.38)", check },
  cool_grey: { light: "#EAEDF0", dark: "#7C8796", coord, lastMove: "rgba(242,169,59,0.38)", check },
  warm_sand: { light: "#F3EAD6", dark: "#A58B5E", coord, lastMove: "rgba(242,169,59,0.38)", check },
};
