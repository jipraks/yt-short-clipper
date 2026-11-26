import { invoke } from "@tauri-apps/api/core";
import type { SessionData } from "@/hooks/highlights";

export interface SessionSummary {
  /** The session folder's name, e.g. 20261126_123301. Clips point back to it. */
  id: string;
  sessionDir: string;
  url: string;
  title: string;
  channel: string;
  highlightCount: number;
  /** Clips with a finished video on disk. */
  renderedCount: number;
  status: string;
  createdAt: string;
}

export async function listSessions(): Promise<SessionSummary[]> {
  return invoke<SessionSummary[]>("list_sessions");
}

export async function loadSession(sessionDir: string): Promise<SessionData> {
  return invoke<SessionData>("load_session", { sessionDir });
}

export async function deleteSession(sessionDir: string): Promise<void> {
  return invoke<void>("delete_session", { sessionDir });
}

/** One finished clip and the session it came from. */
export interface ClipSummary {
  sessionId: string;
  sessionDir: string;
  sessionTitle: string;
  channel: string;
  url: string;
  highlightIndex: number;
  clipPath: string;
  title: string;
  hookText: string;
  description: string;
  startTime: string;
  endTime: string;
  durationSeconds: number;
  reframeMode: string;
  processedAt: string;
}

export async function listClips(): Promise<ClipSummary[]> {
  return invoke<ClipSummary[]>("list_clips");
}

/** "20261126_123301" reads as "#20261126-1233": short, and still sorts by date. */
export function formatSessionId(id: string): string {
  const m = /^(\d{8})_(\d{4})\d{2}$/.exec(id);
  return m ? `#${m[1]}-${m[2]}` : `#${id}`;
}
