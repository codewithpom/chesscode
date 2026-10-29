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
  it("keeps volume in the rendered transform: scaleX * scaleY = 1 within 1e-9", () => {
    const squashes = [...Object.values(POSES).map((s) => s.squash), 1.0123456789, 0.9371];
    for (const squash of squashes) {
      const m = /scale\(([^ )]+) ([^ )]+)\)/.exec(html({ ...POSES.idle, squash }));
      expect(m).not.toBeNull();
      expect(Math.abs(Number(m![1]) * Number(m![2]) - 1)).toBeLessThan(1e-9);
    }
  });
  it("is byte-identical twice", () => {
    for (const s of Object.values(POSES)) expect(html(s)).toBe(html(s));
  });
});
