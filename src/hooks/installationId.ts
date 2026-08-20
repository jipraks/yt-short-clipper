import { loadAppConfig, saveAppConfig } from "@/hooks/appConfig";

/**
 * Returns a stable per-installation UUID. Generated once on first run and
 * persisted in config.json (app data dir), so it survives app updates.
 *
 * The resolving promise is memoized so concurrent callers (e.g. version check
 * and notification check firing on mount) share one load/generate/save and
 * never race to create two different IDs.
 */
let cached: Promise<string> | null = null;

export function getInstallationId(): Promise<string> {
  if (!cached) cached = resolveInstallationId();
  return cached;
}

async function resolveInstallationId(): Promise<string> {
  try {
    const config = await loadAppConfig();
    if (config.installationId && config.installationId.trim() !== "") {
      return config.installationId;
    }
    const id = crypto.randomUUID();
    await saveAppConfig({ ...config, installationId: id });
    return id;
  } catch {
    // If config IO fails, fall back to a session-stable id (memoized above)
    // so the update/notification check still works.
    return crypto.randomUUID();
  }
}
