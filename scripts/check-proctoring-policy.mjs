import assert from "node:assert/strict";
import {
  requirements,
  requiredCheck,
  enabled,
} from "../apps/candidate-desktop/src/proctoring.ts";

const keys = [
  "CAMERA_DISABLED",
  "FACE_ABSENT",
  "MULTIPLE_PERSONS",
  "PHONE_DETECTED",
  "LIVENESS_FAILED",
  "MICROPHONE_DISABLED",
  "BACKGROUND_SPEECH",
  "SCREEN_RECORDING",
  "FULLSCREEN_EXIT",
  "DISPLAY_CHECK",
];
const disabled = Object.fromEntries(
  keys.map((key) => [key, { enabled: false }]),
);
assert.deepEqual(requirements(disabled), {
  face: false,
  phone: false,
  liveness: false,
  camera: false,
  microphone: false,
  screen: false,
  fullscreen: false,
  devices: false,
  sidecar: false,
});
assert.equal(requiredCheck("backend", disabled), true);
for (const key of [
  "camera",
  "microphone",
  "sidecar",
  "screen",
  "devices",
  "fullscreen",
  "liveness",
])
  assert.equal(requiredCheck(key, disabled), false, key);
for (const key of keys) assert.equal(enabled(disabled, key), false, key);
for (const key of ["PHONE_DETECTED", "LIVENESS_FAILED", "FACE_ABSENT"]) {
  const selected = { ...disabled, [key]: { enabled: true } };
  assert.equal(requirements(selected).camera, true, key);
  assert.equal(requirements(selected).sidecar, true, key);
  assert.equal(requirements(selected).screen, false, key);
}
assert.equal(
  requirements(undefined).camera,
  true,
  "Legacy policies retain existing requirements",
);
assert.equal(requirements({}).fullscreen, true);
assert.equal(
  enabled({ CLIPBOARD_COPY: { enabled: false } }, "CLIPBOARD_COPY"),
  false,
);
console.log(
  "Proctoring requirement, dependency, and legacy-policy checks passed.",
);
