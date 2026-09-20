import { PUBLIC_API_BASE } from "@/config/api";

export interface NotificationResponse {
  message: string | null;
  image: string | null;
  link: string | null;
  link_text: string | null;
}

const NOTIFICATION_URL = `${PUBLIC_API_BASE}/notification`;

/** What `GET /notification` actually returns: one envelope, camelCase inside. */
interface NotificationEnvelope {
  notification?: {
    id?: string;
    message?: string | null;
    image?: string | null;
    link?: string | null;
    linkText?: string | null;
  } | null;
}

export async function checkNotification(): Promise<NotificationResponse | null> {
  try {
    const res = await fetch(NOTIFICATION_URL);
    if (!res.ok) return null;

    const body: NotificationEnvelope = await res.json();
    const notice = body?.notification;
    if (!notice?.message) return null;

    return {
      message: notice.message,
      image: notice.image ?? null,
      link: notice.link ?? null,
      link_text: notice.linkText ?? null,
    };
  } catch {
    return null;
  }
}
