export function getByPath(obj: unknown, path: string): number | null {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return null;
    cur = (cur as Record<string, unknown>)[p];
  }
  return typeof cur === "number" ? cur : null;
}

export function formatDollars(value: number | null): string {
  if (value == null) return "—";
  const rounded = Math.round(value);
  const abs = Math.abs(rounded).toLocaleString("en-US");
  return rounded < 0 ? `(${abs})` : abs;
}

export function formatPercent(value: number | null): string {
  if (value == null) return "—";
  const rounded = Math.round(value * 10) / 10;
  const abs = Math.abs(rounded).toFixed(1);
  return rounded < 0 ? `(${abs}%)` : `${abs}%`;
}
