// The only ms <-> frame conversions in the project (docs/SPEC.md section 3).
export const msToFrame = (ms: number, fps: number): number => Math.round((ms * fps) / 1000);
export const frameToMs = (frame: number, fps: number): number => Math.round((frame * 1000) / fps);
