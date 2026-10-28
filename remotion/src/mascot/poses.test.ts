import { describe, expect, it } from "vitest";
import { Pose } from "../spec/schema";
import { POSES } from "./poses";
import { lerpPose, scaleOf } from "./poseState";

describe("POSES", () => {
  it("has a key for every Pose and eyeOpen in [0,1]", () => {
    expect(Object.keys(POSES).sort()).toEqual([...Pose.options].sort());
    for (const s of Object.values(POSES)) {
      expect(s.eyeOpen).toBeGreaterThanOrEqual(0);
      expect(s.eyeOpen).toBeLessThanOrEqual(1);
    }
  });

  it("lerpPose hits both ends and switches ids at 0.5", () => {
    const a = POSES.idle;
    const b = POSES.facepalm;
    expect(lerpPose(a, b, 0)).toEqual(a);
    expect(lerpPose(a, b, 1)).toEqual(b);
    expect(lerpPose(a, b, 0.49).arms).toBe("none");
    expect(lerpPose(a, b, 0.5).arms).toBe("face");
  });

  it("squash conserves volume", () => {
    for (const s of Object.values(POSES)) {
      const { x, y } = scaleOf(s.squash);
      expect(Math.abs(x * y - 1)).toBeLessThan(1e-9);
    }
  });
});
