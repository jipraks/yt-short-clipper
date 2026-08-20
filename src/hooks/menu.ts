import { APP_VERSION } from "@/config/version";
import { getInstallationId } from "@/hooks/installationId";

export interface MenuItem {
  id: string;
  label: string;
  icon: string;
  url: string;
}

const MENU_URL = "https://api.ytclip.org/webhook/yt-clipper/menu";
const CACHE_KEY = "ytclip.sidebar-menu.v1";

/** Guard rails on anything the server sends. */
const MAX_ITEMS = 8;
const MAX_LABEL_CHARS = 32;

/**
 * Shipped with the build and shown on first run, offline, or whenever the API
 * returns nothing usable — the sidebar must never render empty.
 */
export const DEFAULT_MENU_ITEMS: MenuItem[] = [
  { id: "topup", label: "Topup AI Credit", icon: "coins", url: "https://ai.ytclip.org" },
  {
    id: "tutorial",
    label: "Video Tutorial",
    icon: "youtube",
    url: "https://www.youtube.com/playlist?list=PLXvNtebci7kQ",
  },
  { id: "discord", label: "Discord Server", icon: "messages-square", url: "https://s.id/ytsdc" },
];

function sanitizeItem(raw: unknown): MenuItem | null {
  if (!raw || typeof raw !== "object") return null;
  const { id, label, icon, url } = raw as Record<string, unknown>;

  if (typeof id !== "string" || !id.trim()) return null;
  if (typeof label !== "string" || !label.trim()) return null;
  if (typeof url !== "string") return null;

  // https only. These URLs are handed to the OS browser, so the menu endpoint
  // is a channel that can send every user anywhere — refuse anything else.
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (parsed.protocol !== "https:") return null;

  return {
    id: id.trim(),
    label: label.trim().slice(0, MAX_LABEL_CHARS),
    icon: typeof icon === "string" ? icon.trim().toLowerCase() : "",
    url: parsed.toString(),
  };
}

/**
 * Keep the good items and drop the bad ones — one malformed entry should not
 * cost the user their whole menu.
 */
export function sanitizeMenu(raw: unknown): MenuItem[] {
  const items = (raw as { items?: unknown })?.items;
  if (!Array.isArray(items)) return [];

  const seen = new Set<string>();
  const clean: MenuItem[] = [];
  for (const entry of items) {
    const item = sanitizeItem(entry);
    if (!item || seen.has(item.id)) continue;
    seen.add(item.id);
    clean.push(item);
    if (clean.length >= MAX_ITEMS) break;
  }
  return clean;
}

/** Last response that passed validation, so the sidebar is right on first paint. */
export function readCachedMenu(): MenuItem[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const items = sanitizeMenu({ items: JSON.parse(cached) });
    return items.length ? items : null;
  } catch {
    return null;
  }
}

function writeCachedMenu(items: MenuItem[]): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(items));
  } catch {
    // Cache is an optimisation; a full or disabled store is not an error.
  }
}

/**
 * Fetch the menu. Returns null on any failure so the caller keeps showing what
 * it already has — cached items, or the built-in defaults.
 */
export async function fetchMenu(): Promise<MenuItem[] | null> {
  try {
    const installationId = await getInstallationId();
    const url =
      `${MENU_URL}?app_version=${encodeURIComponent(APP_VERSION)}` +
      `&installation_id=${encodeURIComponent(installationId)}`;

    const res = await fetch(url);
    if (!res.ok) return null;

    const items = sanitizeMenu(await res.json());
    if (!items.length) return null;

    writeCachedMenu(items);
    return items;
  } catch {
    return null;
  }
}
