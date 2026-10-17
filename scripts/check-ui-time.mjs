import assert from "node:assert/strict";
import { serverDate as candidateDate } from "../apps/candidate-desktop/src/time.ts";
import { serverDate as portalDate } from "../apps/web-portal/src/time.ts";

const expected = Date.UTC(2026, 9, 17, 8, 36, 50, 359);
for (const parse of [candidateDate, portalDate]) {
  for (const value of [
    "2026-10-17T08:36:50.359057", // Actual SQLite response shape that expired a fresh exam.
    "2026-10-17T08:36:50.359Z",
    "2026-10-17T08:36:50.359+00:00",
    "2026-10-17T14:06:50.359+05:30",
  ])
    assert.equal(parse(value).getTime(), expected, value);
  assert.equal(
    parse("2026-10-17T08:36:50").getTime() +
      30 * 60_000 -
      Date.UTC(2026, 9, 17, 8, 37),
    29 * 60_000 + 50_000,
  );
}
console.log(
  "UTC timestamp and countdown regression checks passed for both portals.",
);
