import { invoke, Channel } from "@tauri-apps/api/core";
import { create } from "zustand";

type ProxyEvent =
  | { type: "log"; message: string }
  | { type: "progress"; percent: number };

export interface ProxyState {
  status: "downloading" | "ready" | "error";
  percent: number;
  path?: string;
  error?: string;
  lastLog?: string;
}

interface ProxyStore {
  bySession: Record<string, ProxyState>;
  patch: (sessionDir: string, next: Partial<ProxyState>) => void;
}

/**
 * Preview-proxy downloads keyed by session folder. Lives outside the editor
 * component so a download keeps going, and keeps reporting, when the user
 * leaves the page and comes back.
 */
export const useProxyStore = create<ProxyStore>((set) => ({
  bySession: {},
  patch: (sessionDir, next) =>
    set((state) => ({
      bySession: {
        ...state.bySession,
        [sessionDir]: {
          ...(state.bySession[sessionDir] ?? { status: "downloading", percent: 0 }),
          ...next,
        },
      },
    })),
}));

const inFlight = new Map<string, Promise<void>>();

/** Start the proxy download for a session unless it is running or done. */
export function ensureProxy(url: string, sessionDir: string): Promise<void> {
  const current = useProxyStore.getState().bySession[sessionDir];
  if (current?.status === "ready") return Promise.resolve();
  const running = inFlight.get(sessionDir);
  if (running) return running;

  const { patch } = useProxyStore.getState();
  patch(sessionDir, { status: "downloading", percent: 0, error: undefined });

  const channel = new Channel<ProxyEvent>();
  channel.onmessage = (event) => {
    if (event.type === "progress") patch(sessionDir, { percent: event.percent });
    else if (event.type === "log") patch(sessionDir, { lastLog: event.message });
  };

  const job = invoke<string>("download_proxy", { url, sessionDir, onEvent: channel })
    .then((path) => patch(sessionDir, { status: "ready", percent: 100, path }))
    .catch((err) => {
      const message = String(err).split("\n\nstderr:")[0].replace(/^Sidecar error: /, "");
      patch(sessionDir, { status: "error", error: message });
    })
    .finally(() => inFlight.delete(sessionDir));

  inFlight.set(sessionDir, job);
  return job;
}
