import { APP_VERSION } from "@/config/version";
import { compareVersions } from "@/utils/version";
import { fetchAppInfo } from "@/hooks/account";

export interface LatestVersionResponse {
  version: string;
  download_url: string;
  changelog: string;
}

/**
 * Whether a newer build exists, or null when this one is current.
 *
 * Reads `GET /app` on the public device API, through the same Rust command the
 * account store uses for the version floor — one endpoint now answers both
 * "are you too old to use in-app AI" and "is there an update". The shape below
 * is kept as-is so the update dialog and the app store do not have to care
 * that the source moved.
 */
export async function checkForUpdate(): Promise<LatestVersionResponse | null> {
  try {
    const info = await fetchAppInfo();
    if (!info?.latestVersion) return null;
    if (compareVersions(APP_VERSION, info.latestVersion) >= 0) return null;

    return {
      version: info.latestVersion,
      download_url: info.downloadUrl ?? "",
      changelog: info.changelog ?? "",
    };
  } catch {
    return null;
  }
}
