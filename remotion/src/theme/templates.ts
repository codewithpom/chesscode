import type { z } from "zod";
import type { Fx } from "../spec/schema";

// Per-template off switch for every beat effect (docs/SPEC.md section 8: "every effect has an off switch
// per template"). Both templates run every effect for now; Editorial could turn board_shake off here.
export type FxId = z.infer<typeof Fx>;
export type TemplateFx = Record<FxId, boolean>;

const allOn: TemplateFx = {
  board_shake: true,
  red_flash: true,
  replay_move: true,
  move_underline: true,
  gold_glint: true,
  stamp_brilliant: true,
  ghost_arrow: true,
  eval_whip: true,
  clock_pulse: true,
  clock_red: true,
  king_trail: true,
  crown_sparkle: true,
  freeze_frame: true,
  out_of_theory_label: true,
};

export const templateFx: Record<"studio" | "shorts", TemplateFx> = {
  studio: { ...allOn },
  shorts: { ...allOn },
};
