import type { ReadinessKey } from "./types";

export type ProctoringRules = Record<
  string,
  { enabled?: boolean; [key: string]: unknown }
>;
export function enabled(rules: ProctoringRules | undefined, key: string) {
  return rules?.[key]?.enabled !== false;
}
export function requirements(rules: ProctoringRules | undefined) {
  const on = (key: string) => enabled(rules, key);
  const face = on("FACE_ABSENT") || on("MULTIPLE_PERSONS");
  const phone = on("PHONE_DETECTED");
  const liveness = on("LIVENESS_FAILED");
  const camera = on("CAMERA_DISABLED") || face || phone || liveness;
  return {
    face,
    phone,
    liveness,
    camera,
    microphone: on("MICROPHONE_DISABLED") || on("BACKGROUND_SPEECH"),
    screen: on("SCREEN_RECORDING"),
    fullscreen: on("FULLSCREEN_EXIT"),
    devices: on("DISPLAY_CHECK"),
    sidecar: face || phone || liveness,
  };
}
export function requiredCheck(
  key: ReadinessKey,
  rules: ProctoringRules | undefined,
): boolean {
  const required = requirements(rules);
  return key === "backend" || required[key];
}
