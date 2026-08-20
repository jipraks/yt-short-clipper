import { APP_VERSION } from "@/config/version";
import { getInstallationId } from "@/hooks/installationId";

export interface NotificationResponse {
  message: string | null;
  image: string | null;
  link: string | null;
  link_text: string | null;
}

const NOTIFICATION_URL = "https://api.ytclip.org/webhook/yt-clipper/notification";

export async function checkNotification(): Promise<NotificationResponse | null> {
  try {
    const installationId = await getInstallationId();
    const url =
      `${NOTIFICATION_URL}?app_version=${encodeURIComponent(APP_VERSION)}` +
      `&installation_id=${encodeURIComponent(installationId)}`;
    const res = await fetch(url);
    if (!res.ok) return null;

    const data: NotificationResponse = await res.json();
    if (data?.message) return data;

    return null;
  } catch {
    return null;
  }
}
