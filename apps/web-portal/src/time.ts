/** SQLite API timestamps without an offset represent UTC, not browser-local time. */
export function serverDate(value: string): Date {
  const hasOffset = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasOffset ? value : `${value}Z`);
}

const indiaTimeZone = "Asia/Kolkata";

export function formatServerDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: indiaTimeZone,
  }).format(serverDate(value));
}

export function formatServerTime(value: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: indiaTimeZone,
  }).format(serverDate(value));
}
