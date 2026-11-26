/** Parse "HH:MM:SS,mmm" (or with a dot) into seconds. */
export function parseTimestamp(ts: string): number {
  const [h = "0", m = "0", s = "0"] = ts.replace(",", ".").split(":");
  return Number(h) * 3600 + Number(m) * 60 + Number(s);
}

/** Seconds into the "HH:MM:SS,mmm" form the sidecar and session file use. */
export function toTimestamp(seconds: number): string {
  const totalMs = Math.max(0, Math.round(seconds * 1000));
  const h = Math.floor(totalMs / 3_600_000);
  const m = Math.floor((totalMs % 3_600_000) / 60_000);
  const s = Math.floor((totalMs % 60_000) / 1000);
  const ms = totalMs % 1000;
  const pad = (n: number, w = 2) => String(n).padStart(w, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)},${pad(ms, 3)}`;
}

/** Editor clock: "1:05.3", or "1:02:05.3" past an hour. */
export function formatClock(seconds: number, decimals = 1): string {
  const safe = Math.max(0, seconds);
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  const sec = s.toFixed(decimals).padStart(decimals ? decimals + 3 : 2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}

/** Ruler label: whole seconds, no decimals. */
export function formatRuler(seconds: number): string {
  return formatClock(Math.round(seconds), 0);
}
