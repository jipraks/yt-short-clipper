import { invoke } from "@tauri-apps/api/core";
import type { SessionData } from "@/hooks/highlights";

export interface SessionSummary {
  sessionDir: string;
  url: string;
  title: string;
  channel: string;
  highlightCount: number;
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
