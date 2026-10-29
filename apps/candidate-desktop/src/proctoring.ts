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
  const identity = true;
  const camera = true;
  return {
    face,
    phone,
    identity,
    camera,
    microphone: on("MICROPHONE_DISABLED") || on("BACKGROUND_SPEECH"),
    screen: on("SCREEN_RECORDING"),
    fullscreen: on("FULLSCREEN_EXIT"),
    devices: on("DISPLAY_CHECK"),
    sidecar: face || phone || identity,
  };
}
export function requiredCheck(
  key: ReadinessKey,
  rules: ProctoringRules | undefined,
): boolean {
  const required = requirements(rules);
  return key === "backend" || required[key];
}
