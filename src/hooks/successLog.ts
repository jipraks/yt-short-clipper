import { APP_VERSION } from "@/config/version";
import { getInstallationId } from "@/hooks/installationId";

const WEBHOOK_URL = "https://api.ytclip.org/webhook/yt-clipper/success-log";

export type ClipSuccessFormat = "face-tracking" | "centered-black" | "centered-blur";

export async function logClipSuccess(params: {
  duration: number;
  format: ClipSuccessFormat;
}): Promise<void> {
  try {
    const installationId = await getInstallationId();
    const url =
      `${WEBHOOK_URL}?installation_id=${encodeURIComponent(installationId)}` +
      `&app_version=${encodeURIComponent(APP_VERSION)}` +
      `&duration=${encodeURIComponent(String(params.duration))}` +
      `&format=${encodeURIComponent(params.format)}`;
    await fetch(url, { method: "GET" });
  } catch {
    // Telemetry must never disrupt the user flow.
  }
}