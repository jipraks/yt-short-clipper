import { invoke } from "@tauri-apps/api/core";
import { APP_VERSION } from "@/config/version";
import { getInstallationId } from "@/hooks/installationId";

/** How a finished clip was framed. Registered in GA4 as a custom dimension. */
export type ReframeFormat =
  | "face-tracking"
  | "centered-black"
  | "centered-blur"
  | "original-16-9";

/**
 * Records one finished clip.
 *
 * Fire-and-forget by contract: the Rust side swallows every failure and the
 * promise is never worth awaiting. Analytics must not be able to interrupt,
 * delay, or fail a render.
 *
 * `duration_seconds` and `reframe_mode` are custom parameters. GA4 collects
 * them from the first event, but they stay invisible in reports until each is
 * registered as a custom dimension/metric in the GA4 admin — and registering
 * does not backfill. Register before shipping a build that sends them.
 */
export function trackClipRendered(params: {
  durationSeconds: number;
  format: ReframeFormat;
}): void {
  void track("clip_rendered", {
    duration_seconds: Math.round(params.durationSeconds * 10) / 10,
    reframe_mode: params.format,
  });
}

async function track(name: string, params: Record<string, unknown>): Promise<void> {
  try {
    const clientId = await getInstallationId();
    await invoke("analytics_track", {
      clientId,
      name,
      params: { ...params, app_version: APP_VERSION },
    });
  } catch {
    // Unreachable in practice — the command returns Ok even when the send
    // fails — but a rejected invoke must not surface either.
  }
}
