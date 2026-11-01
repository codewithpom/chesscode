import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildPositions } from "../board/positions";
import { boardStateAt } from "../board/boardState";
import { VideoSpec } from "../spec/schema";
import { msToFrame } from "../spec/time";
import { moveDoneFrame } from "../board/boardState";
import { layerRects, estimateLines, textHeight } from "../mascot/layerLayout";
import { reactionsFor } from "../mascot/react";
import { strings } from "./strings";
import { sceneRanges } from "./timeline";
import { studioLayout } from "../theme/layout";
import { activeLineMove, captionsBoxAt, clockFor, mascotBeats, mascotPlacement, lineMoves, lineRows, signOffBeats, coldOpenSpec, currentPlyAt, keyMomentTiming, moveLabel, resultText, yearOf } from "./helpers";

const spec = VideoSpec.parse(
  JSON.parse(readFileSync(resolve(__dirname, "../../../spec/fixtures/cc-2026-0001-en/video_spec.json"), "utf8")),
);
const FPS = 30;

describe("coldOpenSpec", () => {
  const range = { startMs: 0, endMs: 5400 };
  const cold = coldOpenSpec(spec, range);
  const positions = buildPositions(spec.game.pgn);
  const at = (ms: number) => boardStateAt(msToFrame(ms, FPS), FPS, cold.plies, positions);

  it("shows the position before ply_from first, with the earlier move already landed and no arrows", () => {
    const s = at(100);
    expect(s.ply).toBe(30);
    expect(s.arrows).toEqual([]);
    expect(s.pieces.map((p) => `${p.id}@${p.x},${p.y}`).sort()).toEqual(
      positions[30].pieces.map((p) => `${p.id}@${p.square.charCodeAt(0) - 97},${8 - Number(p.square[1])}`).sort(),
    );
  });

  it("plays ply_from..ply_to inside the range, in order, and never shows later plies", () => {
    const times = cold.plies.filter((p) => p.ply >= 31 && p.ply <= 33).map((p) => p.show_at_ms);
    expect(times).toEqual([...times].sort((a, b) => a - b));
    expect(times[0]).toBeGreaterThanOrEqual(0);
    expect(times[2] + 280).toBeLessThanOrEqual(5400);
    expect(at(5399).ply).toBe(33);
    expect(cold.plies.find((p) => p.ply === 34)).toBeUndefined(); // the fixture ends at ply 33
  });

  it("leaves the input untouched", () => {
    expect(spec.plies[30].show_at_ms).not.toBe(cold.plies[30].show_at_ms);
  });
});

describe("small helpers", () => {
  it("currentPlyAt", () => {
    expect(currentPlyAt(spec.plies, 0, FPS)).toBe(null);
    expect(currentPlyAt(spec.plies, msToFrame(spec.plies[4].show_at_ms, FPS), FPS)).toBe(5);
  });
  it("clockFor finds the latest clock of that side", () => {
    const plies = [
      { ply: 1, clock_ms: 600 },
      { ply: 2, clock_ms: 590 },
      { ply: 3, clock_ms: null },
      { ply: 4, clock_ms: 580 },
    ];
    expect(clockFor(plies, "white", 4)).toBe(600);
    expect(clockFor(plies, "black", 4)).toBe(580);
    expect(clockFor(plies, "black", 1)).toBe(null);
    expect(clockFor(spec.plies, "white", 20)).toBe(null); // fixture has no clock data
  });
  it("yearOf, resultText, moveLabel", () => {
    expect(yearOf("1858-11-02")).toBe("1858");
    expect(yearOf("1858.??.??")).toBe("1858");
    expect(yearOf("?")).toBe("");
    expect(resultText("1/2-1/2")).toBe("½–½");
    expect(moveLabel({ ply: 19, san: "Bxb5+" })).toBe("10. Bxb5+");
    expect(moveLabel({ ply: 20, san: "Qxb5" })).toBe("10...Qxb5");
  });
});

describe("keyMomentTiming", () => {
  const lastDone = (durationMs: number, moves: number) => {
    const { leadMs, stepMs } = keyMomentTiming(durationMs, moves);
    return moveDoneFrame(leadMs + (moves - 1) * stepMs, FPS);
  };

  it("an 8-move line in a 15 s scene plays to its end (it used to start the last move at 15.5 s)", () => {
    const { leadMs, stepMs } = keyMomentTiming(15000, 8);
    expect(leadMs + 7 * stepMs).toBeLessThan(15000);
    expect(lastDone(15000, 8)).toBeLessThanOrEqual(msToFrame(15000 - 1000, FPS)); // landed with the hold still to go
    expect(stepMs).toBeLessThan(2000); // below the old 2 s floor, as the scene demands
  });

  it("every line length in every legal scene length finishes with the hold and moves one at a time", () => {
    for (let moves = 1; moves <= 8; moves++)
      for (let seconds = 15; seconds <= 40; seconds += 5) {
        const { leadMs, stepMs } = keyMomentTiming(seconds * 1000, moves);
        expect(lastDone(seconds * 1000, moves), `${moves} moves in ${seconds} s`).toBeLessThanOrEqual(msToFrame(seconds * 1000 - 1000, FPS));
        if (moves > 1) expect(stepMs, `${moves} moves in ${seconds} s`).toBeGreaterThanOrEqual(280);
        expect(leadMs).toBeGreaterThanOrEqual(0);
      }
  });

  it("a short line in a long scene is not stretched past 4.5 s a move", () => {
    expect(keyMomentTiming(40000, 2).stepMs).toBe(4500);
  });
});

describe("captionsBoxAt", () => {
  const ranges = sceneRanges(spec); // cold open, playback, outro (from 40 s)
  const outroStart = ranges.find((r) => r.kind === "outro")!.startMs;

  it("keeps the right column until the outro, then moves the captions to the left third", () => {
    expect(captionsBoxAt(ranges, 1000)).toBeUndefined();
    expect(captionsBoxAt(ranges, outroStart - 1)).toBeUndefined();
    const box = captionsBoxAt(ranges, outroStart)!;
    expect(box).toBe(studioLayout.boxes.outroCaptions);
    expect(box.x + box.w).toBeLessThanOrEqual(studioLayout.width / 3);
  });

  it("outro captions never touch the end-screen area, whatever outro narration there is", () => {
    // A spoken outro that runs 6 s: every ms of it uses the left-third box.
    const spoken = ranges.map((r) => (r.kind === "outro" ? { ...r, endMs: r.startMs + 6000 } : r));
    for (let ms = outroStart; ms < outroStart + 6000; ms += 250) {
      const b = captionsBoxAt(spoken, ms)!;
      expect(b.x + b.w).toBeLessThanOrEqual(640);
    }
  });
});

describe("signOffBeats", () => {
  const range = { startMs: 40000 };
  for (const lang of ["en", "hi"] as const) {
    const beats = signOffBeats({ ...spec, language: lang }, range);

    it(`${lang}: Pyaada waves, then points, one after the other inside the outro`, () => {
      expect(beats.map((b) => b.mascot.pose)).toEqual(["wave", "point"]);
      expect(beats[0].at_ms).toBeGreaterThanOrEqual(range.startMs);
      const rs = reactionsFor(beats, FPS, 1800);
      expect(rs[0].bubbleTo).toBeLessThan(rs[1].reactFrame); // the wave bubble is gone before the point starts
    });

    it(`${lang}: short lines (8 words English, 10 Hindi) that fit the outro bubble`, () => {
      const { bubble } = layerRects(studioLayout.boxes.outroMascot, studioLayout.outroMascotHeight);
      for (const b of beats) {
        expect(b.mascot.line.split(" ").length).toBeLessThanOrEqual(lang === "en" ? 8 : 10);
        expect(textHeight(estimateLines(b.mascot.line, bubble.w))).toBeLessThanOrEqual(bubble.h);
      }
      expect(beats[0].mascot.line).toBe(strings[lang].signOffWave);
    });
  }
});

describe("captionsBoxAt in scenes without a board", () => {
  const ranges = [
    { kind: "cold_open" as const, startMs: 0, endMs: 6000 },
    { kind: "title" as const, startMs: 6000, endMs: 8800 },
    { kind: "player_intro" as const, startMs: 8800, endMs: 14000 },
    { kind: "playback" as const, startMs: 14000, endMs: 20000 },
  ];
  it("the title card and the player intro start at x = 96, the board scenes keep the right column", () => {
    expect(captionsBoxAt(ranges, 1000)).toBeUndefined();
    expect(captionsBoxAt(ranges, 7000)).toBe(studioLayout.boxes.fullCaptions);
    expect(captionsBoxAt(ranges, 10000)).toBe(studioLayout.boxes.fullCaptions);
    expect(captionsBoxAt(ranges, 15000)).toBeUndefined();
    expect(studioLayout.boxes.fullCaptions.x).toBe(96);
  });
});

describe("the key-moment line as rows", () => {
  const FEN_BLACK = "rnbqkbnr/ppp1pppp/8/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R b KQkq - 1 2"; // after 1.d4 d5 2.Nf3: Black to move, move 2
  const line = ["g8f6", "c2c4", "e7e6", "b1c3"];
  const moves = lineMoves(FEN_BLACK, line);

  it("numbers the moves from the position, a Black-first line starting on move 2 with Black", () => {
    expect(moves).toEqual([
      { no: 2, side: "b", san: "Nf6" },
      { no: 3, side: "w", san: "c4" },
      { no: 3, side: "b", san: "e6" },
      { no: 4, side: "w", san: "Nc3" },
    ]);
  });

  it("reveals the line move by move and marks the move on show", () => {
    expect(lineRows(moves, 0)).toEqual([{ no: 2, black: "Nf6", current: "b" }]);
    expect(lineRows(moves, 2)).toEqual([
      { no: 2, black: "Nf6", current: null },
      { no: 3, white: "c4", black: "e6", current: "b" },
    ]);
    expect(lineRows(moves, 3)[2]).toEqual({ no: 4, white: "Nc3", current: "w" });
  });

  it("the active move follows the board: the arrow move while it waits, the sliding move while it plays", () => {
    const step = 2000;
    expect(activeLineMove(-500, step, 4)).toBe(0);
    expect(activeLineMove(100, step, 4)).toBe(0);
    expect(activeLineMove(300, step, 4)).toBe(1);
    expect(activeLineMove(3 * step + 300, step, 4)).toBe(3);
    expect(activeLineMove(10 * step, step, 4)).toBe(3);
  });
});

describe("one mascot layer for the whole video", () => {
  const gallery = VideoSpec.parse(JSON.parse(readFileSync(resolve(__dirname, "../../../spec/fixtures/gallery-en/video_spec.json"), "utf8")));
  const ranges = sceneRanges(gallery);
  const beats = mascotBeats(gallery, ranges);
  const total = msToFrame(gallery.duration_ms, FPS);
  const rs = reactionsFor(beats, FPS, total);

  it("has the game's beats, the cold open's silent replay and the two sign-off beats, each its own reaction", () => {
    expect(new Set(beats.map((b) => b.beat_id)).size).toBe(beats.length);
    expect(beats.map((b) => b.mascot.pose)).toEqual(expect.arrayContaining(["slow_clap", "faint", "wave", "point"]));
    expect(beats.filter((b) => b.beat_id.endsWith("-cold")).every((b) => b.mascot.line === "")).toBe(true);
  });

  it("a reaction crossing a scene cut keeps its bubble: the brilliant beat's bubble runs past the Playback to Verdict cut", () => {
    const cut = msToFrame(47000, FPS);
    const r = rs.find((x) => x.beat.beat_id === "b-02")!;
    expect(r.bubbleFrom).toBeLessThan(cut);
    expect(r.bubbleTo).toBeGreaterThan(cut);
    expect(r.bubbleTo).toBeGreaterThanOrEqual(r.bubbleFrom + msToFrame(1800, FPS)); // not clamped to the scene end
  });

  it("the box does not change at a cut between scenes that share the mascot box (faint across Playback to KeyMoment, brilliant across Playback to Verdict)", () => {
    for (const cut of [27000, 47000]) {
      const before = mascotPlacement(ranges, cut - 1);
      const after = mascotPlacement(ranges, cut);
      expect(before).not.toBeNull();
      expect(after).toEqual(before);
    }
  });

  it("scenes with no room for him (title card, player intro) have no mascot", () => {
    expect(mascotPlacement(ranges, 7000)).toBeNull();
    expect(mascotPlacement(ranges, 10000)).toBeNull();
    expect(mascotPlacement(ranges, 58000)?.box).toBe(studioLayout.boxes.outroMascot);
  });
});
