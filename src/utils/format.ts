/**
 * Format seconds to MM:SS or HH:MM:SS
 */
export function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);

  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * Format a timestamp for log display
 */
export function formatLogTime(ts: number): string {
  const date = new Date(ts);
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/** Rupiah, the way an Indonesian invoice reads it: "Rp169.000". */
export function formatIdr(amount: number): string {
  return `Rp${new Intl.NumberFormat("id-ID").format(Math.round(amount))}`;
}

/**
 * Dollars for a balance. Two decimals reads as money; per-request spend is far
 * smaller than a cent and wants `formatSpendUsd` instead.
 */
export function formatUsd(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

/** Per-request spend. Six decimals, because one call often costs $0.000429. */
export function formatSpendUsd(amount: number): string {
  return `$${amount.toFixed(6)}`;
}

/** "4:32" until the given instant, or null once it has passed. */
export function countdownTo(iso: string | null): string | null {
  if (!iso) return null;
  const remaining = new Date(iso).getTime() - Date.now();
  if (!Number.isFinite(remaining) || remaining <= 0) return null;
  return formatTime(remaining / 1000);
}
