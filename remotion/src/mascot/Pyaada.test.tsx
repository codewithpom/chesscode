import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Pyaada } from "./Pyaada";
import { POSES } from "./poses";

const html = (s = POSES.idle) => renderToStaticMarkup(<Pyaada state={s} height={200} />);

describe("Pyaada", () => {
  it("renders every pose", () => {
    for (const [name, s] of Object.entries(POSES)) expect(html(s), name).toContain('id="head"');
  });
  it('renders no prop group for prop "none"', () => {
    expect(html({ ...POSES.idle, prop: "none" })).not.toContain('id="prop"');
    expect(html()).toContain('id="prop"');
  });
  it("draws arms only when arms is not none", () => {
    expect(html()).not.toContain('id="arm-');
    expect(html(POSES.facepalm)).toContain('id="arm-r"');
  });
  it("is byte-identical twice", () => {
    for (const s of Object.values(POSES)) expect(html(s)).toBe(html(s));
  });
});
