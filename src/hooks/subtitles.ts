import { invoke } from "@tauri-apps/api/core";

export interface SubtitleItem {
  code: string;
  name: string;
}

export interface SubtitleListResponse {
  subtitles: SubtitleItem[];
  automaticCaptions: SubtitleItem[];
  /** Original-language auto-caption code (e.g. "id-orig"), or null.
   *  Word-by-word captions are only possible when this is present. */
  captionOrigCode: string | null;
  error: string | null;
}

export interface SubtitleOption extends SubtitleItem {
  type: "manual" | "auto";
}

export async function getAvailableSubtitles(url: string): Promise<SubtitleListResponse> {
  return invoke<SubtitleListResponse>("get_available_subtitles", { url });
}

export function normalizeSubtitleOptions(result: SubtitleListResponse): SubtitleOption[] {
  return [
    ...(result.subtitles ?? []).map((item) => ({ ...item, type: "manual" as const })),
    ...(result.automaticCaptions ?? []).map((item) => ({ ...item, type: "auto" as const })),
  ];
}
