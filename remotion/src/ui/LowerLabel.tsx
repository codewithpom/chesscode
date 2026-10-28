import type { FC } from "react";
import { LabelPlate } from "./ChapterCard";

/** The key-moment label (`key_moments[].label`, at most 40 characters), in the same slot as chapter cards. */
export const LowerLabel: FC<{ text: string; startMs: number; endMs: number; lang: "en" | "hi" }> = (props) => (
  <LabelPlate {...props} />
);
