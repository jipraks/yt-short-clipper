/** Compare two semantic-ish version strings like "2.0.0-beta" vs "0.1.2".
 * Returns:
 *   > 0 if local > remote
 *   < 0 if local < remote (update available)
 *   0 if equal
 */
export function compareVersions(local: string, remote: string): number {
  const normalize = (v: string) =>
    v
      .toLowerCase()
      .replace(/^[v]/, "")
      .split(/[-+]/)[0]
      .split(".")
      .map((n) => parseInt(n, 10) || 0);

  const a = normalize(local);
  const b = normalize(remote);
  const maxLen = Math.max(a.length, b.length);

  for (let i = 0; i < maxLen; i++) {
    const ai = a[i] ?? 0;
    const bi = b[i] ?? 0;
    if (ai !== bi) return ai - bi;
  }

  // For pre-release suffixes (beta, alpha, rc) treat plain as newer than pre-release.
  const suffixRank = (v: string) => {
    if (v.includes("-alpha")) return 1;
    if (v.includes("-beta")) return 2;
    if (v.includes("-rc")) return 3;
    return 4;
  };
  const rankDiff = suffixRank(local) - suffixRank(remote);
  if (rankDiff !== 0) return rankDiff;

  return 0;
}
