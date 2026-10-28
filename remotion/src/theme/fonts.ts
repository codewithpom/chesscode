import { useEffect } from "react";
import { useDelayRender } from "remotion";
import mono400 from "../assets/fonts/IBMPlexMono-Regular.woff2";
import mono500 from "../assets/fonts/IBMPlexMono-Medium.woff2";
import sans400 from "../assets/fonts/IBMPlexSans-Regular.woff2";
import sans500 from "../assets/fonts/IBMPlexSans-Medium.woff2";
import sans600 from "../assets/fonts/IBMPlexSans-SemiBold.woff2";
import cond600 from "../assets/fonts/IBMPlexSansCondensed-SemiBold.woff2";
import dev400 from "../assets/fonts/IBMPlexSansDevanagari-Regular.woff2";
import dev500 from "../assets/fonts/IBMPlexSansDevanagari-Medium.woff2";
import dev600 from "../assets/fonts/IBMPlexSansDevanagari-SemiBold.woff2";
import { font } from "./tokens";

const FACES: Array<[family: string, weight: string, src: string]> = [
  ["IBM Plex Sans", "400", sans400],
  ["IBM Plex Sans", "500", sans500],
  ["IBM Plex Sans", "600", sans600],
  ["IBM Plex Sans Condensed", "600", cond600],
  ["IBM Plex Mono", "400", mono400],
  ["IBM Plex Mono", "500", mono500],
  ["IBM Plex Sans Devanagari", "400", dev400],
  ["IBM Plex Sans Devanagari", "500", dev500],
  ["IBM Plex Sans Devanagari", "600", dev600],
];

let loading: Promise<void> | null = null;
const loadAll = (): Promise<void> => {
  loading ??= Promise.all(
    FACES.map(async ([family, weight, src]) => {
      const face = await new FontFace(family, `url(${src}) format("woff2")`, { weight }).load();
      document.fonts.add(face);
    }),
  ).then(() => undefined);
  return loading;
};

/** Registers all four Plex families; holds the render until they are ready. */
export const useFonts = (): void => {
  const { delayRender, continueRender, cancelRender } = useDelayRender();
  useEffect(() => {
    const handle = delayRender("Loading IBM Plex fonts");
    loadAll().then(() => continueRender(handle), (e: unknown) => cancelRender(e));
  }, [delayRender, continueRender, cancelRender]);
};

export const fontFor = (lang: "en" | "hi", role: "ui" | "title" | "mono"): string => {
  if (role === "mono") return font.mono;
  if (lang === "hi") return font.devanagari; // Devanagari has no condensed cut; one family keeps Hindi consistent
  return role === "title" ? font.condensed : font.sans;
};
