import { APP_VERSION } from "@/config/version";
import { compareVersions } from "@/utils/version";
import { getInstallationId } from "@/hooks/installationId";

export interface LatestVersionResponse {
  version: string;
  download_url: string;
  changelog: string;
}

const WEBHOOK_URL = "https://api.ytclip.org/webhook/yt-clipper/latest-version";

export async function checkForUpdate(): Promise<LatestVersionResponse | null> {
  try {
    const installationId = await getInstallationId();
    const url =
      `${WEBHOOK_URL}?app_version=${encodeURIComponent(APP_VERSION)}` +
      `&installation_id=${encodeURIComponent(installationId)}`;
    const res = await fetch(url);
    if (!res.ok) return null;

    const data: LatestVersionResponse = await res.json();
    if (!data?.version) return null;

    if (compareVersions(APP_VERSION, data.version) < 0) {
      return data;
    }

    return null;
  } catch {
    return null;
  }
}
