import { describe, expect, it } from "vitest";
import { commonFields, ratingLine } from "./PlayerCard";

const player = (over: Partial<Parameters<typeof commonFields>[0]>) => ({ name: "X", rating: null, title: null, country: null, fact: "f", ...over });

describe("commonFields", () => {
  it("a field shows only when both players have it", () => {
    const morphy = player({ country: "US" });
    const nobles = player({});
    expect(commonFields(morphy, nobles)).toEqual({ title: false, rating: false, country: false }); // Morphy's "US" alone would be lopsided
    const gm = player({ title: "GM", rating: 2850, country: "NO" });
    const other = player({ title: "GM", rating: 2800, country: "US" });
    expect(commonFields(gm, other)).toEqual({ title: true, rating: true, country: true });
    expect(commonFields(gm, player({ rating: 2700 }))).toEqual({ title: false, rating: true, country: false });
  });

  it("ratingLine honours the fields", () => {
    const gm = player({ title: "GM", rating: 2850 });
    expect(ratingLine(gm)).toBe("GM 2850");
    expect(ratingLine(gm, { title: false, rating: true, country: true })).toBe("2850");
    expect(ratingLine(gm, { title: false, rating: false, country: true })).toBe("");
  });
});
