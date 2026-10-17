/** SQLite API timestamps without an offset represent UTC, not browser-local time. */
export function serverDate(value: string): Date {
  const hasOffset = /(?:z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasOffset ? value : `${value}Z`);
}
