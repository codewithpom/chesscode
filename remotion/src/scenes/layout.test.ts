import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { fxWindows } from "../fx/windows";
import { estimateLines, layerRects, textHeight } from "../mascot/layerLayout";
import { RIG } from "../mascot/Pyaada";
import { faintEnd, phaseAt, poseAt, reactionsFor } from "../mascot/react";
import { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { shortsLayout, studioLayout, youtubeShortsUi, type Box } from "../theme/layout";
import { HOOK_BOX, HOOK_SIZE, hookEndMs } from "../compositions/ShortsVideo";
import { sceneRanges } from "./timeline";

const read = (name: string) =>
  VideoSpec.parse(JSON.parse(readFileSync(resolve(__dirname, `../../../spec/fixtures/${name}/video_spec.json`), "utf8")));
const spec = read("cc-2026-0001-en");
const shorts = read("cc-2026-0002-en");
const FPS = 30;
const b = studioLayout.boxes;
const hit = (p: Box, q: Box): boolean => p.x < q.x + q.w && q.x < p.x + p.w && p.y < q.y + q.h && q.y < p.y + p.h;
const inside = (inner: Box, outer: Box): boolean =>
  inner.x >= outer.x && inner.y >= outer.y && inner.x + inner.w <= outer.x + outer.w && inner.y + inner.h <= outer.y + outer.h;

// Real mascot bounds: Pyaada and his bubble as the layer places them inside the mascot box.
const { mascot: pyaada, bubble } = layerRects(b.mascot, studioLayout.mascotHeight);

const boardColumn = { board: b.board, evalBar: b.evalBar, evalLabel: b.evalLabel, rankLabels: b.rankLabels, fileLabels: b.fileLabels };
// What each scene draws. Playback shows the cards or, while a chapter card / label is up, the label instead.
const shown: Record<string, Record<string, Box>> = {
  playback: { cards: b.cards, moveList: b.moveList, mascotBox: b.mascot, pyaada, bubble, captions: b.captions },
  playback_label: { label: b.label, moveList: b.moveList, mascotBox: b.mascot, pyaada, bubble, captions: b.captions },
  cold_open: { hook: b.hook, mascotBox: b.mascot, pyaada, bubble, captions: b.captions },
  key_moment: { label: b.label, line: b.moveList, mascotBox: b.mascot, pyaada, bubble, captions: b.captions },
  title_card: { fullCaptions: b.fullCaptions },
  outro: {
    outroMascot: b.outroMascot,
    outroPyaada: layerRects(b.outroMascot, studioLayout.outroMascotHeight).mascot,
    outroCaptions: b.outroCaptions,
  },
};
// pyaada and bubble are inside mascotBox by construction; only the box is compared against the other boxes.
const independent = (boxes: Record<string, Box>): Record<string, Box> => {
  const { pyaada: _p, bubble: _b, outroPyaada: _o, ...rest } = boxes;
  return rest;
};

const NO_BOARD = ["outro", "title_card"]; // scenes with no board: only the left third / the captions line are drawn
const sceneSet = (kind: string, labelUp: boolean): string => (kind === "playback" && labelUp ? "playback_label" : kind);

const beatFrames = (s: VideoSpec): number[] => {
  const frames = new Set<number>();
  for (const beat of s.beats) {
    const at = msToFrame(beat.at_ms, FPS);
    frames.add(at);
    frames.add(at + 10);
  }
  for (const w of fxWindows(s.beats, FPS)) frames.add(w.from);
  return [...frames];
};

describe("Studio layout at every beat frame of the fixture", () => {
  const ranges = sceneRanges(spec);
  const frames = beatFrames(spec);

  it("has beat frames to check", () => expect(frames.length).toBeGreaterThanOrEqual(4));

  it.each(frames)("frame %i: mascot, bubble, captions, move list and labels clear the board and eval bar and each other", (frame) => {
    const ms = (frame * 1000) / FPS;
    const scene = ranges.find((r) => ms >= r.startMs && ms < r.endMs)!;
    // A label may be up at any beat frame (out-of-theory starts at its beat): check both slot occupants.
    for (const labelUp of [false, true]) {
      const boxes = shown[sceneSet(scene.kind, labelUp)] ?? {};
      const names = Object.keys(independent(boxes));
      for (const n of names) {
        if (scene.kind !== "outro") for (const [bn, bb] of Object.entries(boardColumn)) expect(hit(boxes[n], bb), `${n} vs ${bn}`).toBe(false);
        else expect(boxes[n].x + boxes[n].w, `${n} stays in the left third`).toBeLessThanOrEqual(studioLayout.width / 3);
      }
      for (let i = 0; i < names.length; i++)
        for (let j = i + 1; j < names.length; j++) expect(hit(boxes[names[i]], boxes[names[j]]), `${names[i]} vs ${names[j]}`).toBe(false);
    }
  });

  it("every scene's boxes avoid each other, the board column and the real mascot and bubble bounds", () => {
    for (const [kind, boxes] of Object.entries(shown)) {
      const names = Object.keys(independent(boxes));
      for (let i = 0; i < names.length; i++) {
        if (!NO_BOARD.includes(kind)) for (const bb of Object.values(boardColumn)) expect(hit(boxes[names[i]], bb), `${kind}: ${names[i]}`).toBe(false);
        for (let j = i + 1; j < names.length; j++) expect(hit(boxes[names[i]], boxes[names[j]]), `${kind}: ${names[i]} vs ${names[j]}`).toBe(false);
      }
      // The drawn mascot and bubble stay inside their box and clear of everything else in the scene.
      const box = kind === "outro" ? boxes.outroMascot : boxes.mascotBox;
      if (!box) continue;
      for (const [n, rect] of Object.entries(boxes)) {
        if (n === "pyaada" || n === "bubble" || n === "outroPyaada") {
          expect(inside(rect, box), `${kind}: ${n} inside its box`).toBe(true);
          for (const [on, ob] of Object.entries(independent(boxes))) if (ob !== box) expect(hit(rect, ob), `${kind}: ${n} vs ${on}`).toBe(false);
        }
      }
    }
    expect(hit(pyaada, bubble)).toBe(false);
  });

  it("follows the spec: 96 px margins, board 800 centred, eval bar 24 px 16 px left of the board", () => {
    const { width, height } = studioLayout;
    expect(b.board).toEqual({ x: 136, y: 140, w: 800, h: 800 });
    expect(b.board.y + b.board.h / 2).toBe(height / 2);
    expect(b.evalBar.x + b.evalBar.w + 16).toBe(b.board.x);
    expect(b.evalBar.w).toBe(24);
    for (const n of ["label", "cards", "moveList", "mascot", "captions", "hook"] as const) {
      const bx = b[n];
      expect(bx.x, n).toBeGreaterThanOrEqual(1000);
      expect(bx.x + bx.w, n).toBeLessThanOrEqual(width - 96);
      expect(bx.y, n).toBeGreaterThanOrEqual(96);
      expect(bx.y + bx.h, n).toBeLessThanOrEqual(height - 96);
    }
    expect(b.moveList.h).toBe(studioLayout.moveRows * studioLayout.moveRowHeight);
    expect(b.mascot.h).toBe(studioLayout.mascotHeight);
    for (const n of ["outroMascot", "outroCaptions"] as const) expect(b[n].x + b[n].w, n).toBeLessThanOrEqual(width / 3); // the right two thirds stay empty
  });

  it("the bubble has room: the longest English and a 10-word Hindi line fit the real bubble", () => {
    expect(bubble.w).toBeGreaterThanOrEqual(440);
    expect(bubble.h).toBeLessThanOrEqual(b.mascot.h);
  });
});

/** AABB of the mascot rect while it is rotated about its ground point and shifted, over every frame of every faint. */
const faintBounds = (s: VideoSpec, box: Box, height: number, frameCount: number): Box[] => {
  const { mascot } = layerRects(box, height);
  const k = height / RIG.h;
  const px = mascot.x + RIG.groundX * k;
  const py = mascot.y + RIG.groundY * k;
  const reactions = reactionsFor(s.beats, FPS, frameCount);
  const out: Box[] = [];
  for (const r of reactions) {
    if (r.beat.mascot.pose !== "faint") continue;
    const end = faintEnd({ beatId: r.beat.beat_id, pose: "faint", start: r.reactFrame }, FPS);
    for (let f = r.reactFrame; f <= end; f++) {
      const st = poseAt(f, reactions, FPS, s.video_id);
      const a = (st.lean * Math.PI) / 180;
      const xs: number[] = [];
      const ys: number[] = [];
      for (const [cx, cy] of [[mascot.x, mascot.y], [mascot.x + mascot.w, mascot.y], [mascot.x, mascot.y + mascot.h], [mascot.x + mascot.w, mascot.y + mascot.h]]) {
        const dx = cx - px;
        const dy = cy - py;
        xs.push(px + dx * Math.cos(a) - dy * Math.sin(a) + st.offsetX * k);
        ys.push(py + dx * Math.sin(a) + dy * Math.cos(a) + st.offsetY * k);
      }
      out.push({ x: Math.min(...xs), y: Math.min(...ys), w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) });
    }
  }
  return out;
};

describe("faint unclips the mascot for 57 frames: it never reaches the board or eval bar", () => {
  // A faint on every beat of a copy of the spec, so the fall is checked wherever the beats are.
  const fainting = (s: VideoSpec): VideoSpec => ({
    ...s,
    beats: s.beats.map((beat) => ({ ...beat, mascot: { ...beat.mascot, pose: "faint" as const } })),
  });

  it("has frames to check", () => {
    expect(faintBounds(fainting(spec), b.mascot, studioLayout.mascotHeight, msToFrame(spec.duration_ms, FPS)).length).toBeGreaterThan(50);
  });

  it("Studio: clear of the board, eval bar, their labels and the move list", () => {
    const bounds = faintBounds(fainting(spec), b.mascot, studioLayout.mascotHeight, msToFrame(spec.duration_ms, FPS));
    for (const box of bounds) {
      for (const [n, bb] of Object.entries(boardColumn)) expect(hit(box, bb), `faint vs ${n}`).toBe(false);
      expect(hit(box, b.moveList), "faint vs moveList").toBe(false);
    }
  });

  it("Shorts: clear of the board, eval bar and captions", () => {
    const sb = shortsLayout.boxes;
    const bounds = faintBounds(fainting(shorts), sb.mascot, shortsLayout.mascotHeight, msToFrame(shorts.duration_ms, FPS));
    expect(bounds.length).toBeGreaterThan(50);
    for (const box of bounds) for (const n of ["board", "evalBar", "evalLabel", "captions", "rankLabels"] as const) expect(hit(box, sb[n]), `faint vs ${n}`).toBe(false);
  });

  it("phaseAt knows a faint is in progress only while it is", () => {
    const rs = reactionsFor(fainting(spec).beats, FPS, 3000);
    expect(phaseAt(rs[0].reactFrame, rs, FPS)?.pose).toBe("faint");
  });
});

describe("Shorts mascot box", () => {
  const sb = shortsLayout.boxes;
  const { mascot, bubble: sBubble } = layerRects(sb.mascot, shortsLayout.mascotHeight);
  it("Pyaada (260 px) and his bubble fit the box and stay out of the YouTube zones and the board", () => {
    expect(inside(mascot, sb.mascot) && inside(sBubble, sb.mascot)).toBe(true);
    expect(hit(mascot, sBubble)).toBe(false);
    for (const r of [mascot, sBubble, sb.mascot]) {
      expect(r.x + r.w).toBeLessThanOrEqual(youtubeShortsUi.rightZoneX);
      expect(r.y + r.h).toBeLessThanOrEqual(youtubeShortsUi.bottomZoneY);
    }
    expect(hit(mascot, sb.board) || hit(sBubble, sb.board)).toBe(false);
  });
});

describe("Shorts type is phone-sized", () => {
  const sb = shortsLayout.boxes;
  const { bubble: sBubble } = layerRects(sb.mascot, shortsLayout.mascotHeight, shortsLayout.maxBubbleH);

  it("bubble 44 px, eval label 36 px, hook 72 px or more", () => {
    expect(shortsLayout.bubbleFont).toBeGreaterThanOrEqual(44);
    expect(shortsLayout.evalLabelSize).toBeGreaterThanOrEqual(36);
    expect(HOOK_SIZE).toBeGreaterThanOrEqual(72);
    expect(sb.evalLabel.h).toBeGreaterThanOrEqual(shortsLayout.evalLabelSize);
  });

  it("the longest English line and a 10-word Hindi line fit the 44 px bubble inside the box", () => {
    expect(sBubble.y).toBeGreaterThanOrEqual(sb.mascot.y);
    expect(sBubble.y + sBubble.h).toBeLessThanOrEqual(sb.mascot.y + sb.mascot.h);
    for (const line of ["Two pieces. That's all he needed.", "यह चाल देखकर प्यादा भी सोच में पड़ गया, भाई"]) {
      expect(textHeight(estimateLines(line, sBubble.w, shortsLayout.bubbleFont), shortsLayout.bubbleFont), line).toBeLessThanOrEqual(sBubble.h);
    }
  });

  it("the hook plate (three lines at 72 px) stays above the board and clear of the YouTube zones", () => {
    expect(HOOK_BOX.y + HOOK_BOX.h).toBeLessThanOrEqual(sb.board.y);
    expect(HOOK_BOX.h).toBeGreaterThanOrEqual(3 * HOOK_SIZE * 1.05);
    expect(sb.captions.x + sb.captions.w).toBeLessThanOrEqual(youtubeShortsUi.rightZoneX);
  });

  it("the hook is up for a second, or until the first caption word when that is later", () => {
    expect(hookEndMs(shorts)).toBe(1000);
    const late = { ...shorts, narration: [{ ...shorts.narration[0], words: [{ ...shorts.narration[0].words[0], start_ms: 1600, end_ms: 1900 }, ...shorts.narration[0].words.slice(1)] }, ...shorts.narration.slice(1)] };
    expect(hookEndMs(late)).toBe(1600);
  });
});
