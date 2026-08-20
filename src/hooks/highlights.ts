import { invoke, Channel } from "@tauri-apps/api/core";

export interface Highlight {
  start_time: string;
  end_time: string;
  title: string;
  description: string;
  virality_score: number;
  hook_text: string;
  duration_seconds: number;
  transcript_text?: string;
}

export interface VideoInfo {
  title: string;
  description: string;
  channel: string;
}

export interface SessionData {
  session_dir: string;
  url: string;
  srt_path: string;
  subtitle_language: string;
  /** Free-text steer the user typed on the Create page, or null if none. */
  user_direction?: string | null;
  /** Output-language choice: a code, or "auto" to follow the video. */
  output_language?: string;
  /** Resolved language name the AI wrote in, e.g. "Indonesian". */
  output_language_name?: string;
  /** Whether the source video had an original subtitle track usable for captions. */
  caption_available?: boolean;
  caption_words_path?: string | null;
  highlights: Highlight[];
  video_info: VideoInfo;
  token_usage: { prompt_tokens: number; completion_tokens: number };
  created_at: string;
  status: string;
  processed_highlights?: number[];
}

export interface AIRequestSettings {
  api_key: string;
  base_url: string;
  model: string;
  system_message?: string;
  temperature?: number;
}

export type FindHighlightsEvent = { type: "log"; message: string };

export async function findHighlights(params: {
  url: string;
  numClips: number;
  subtitleLanguage: string;
  ai: AIRequestSettings;
  /** Optional free-text steer injected into the highlight prompt. */
  userDirection?: string;
  /** Language code for titles and hooks, or "auto" to follow the video. */
  outputLanguage?: string;
  onLog?: (message: string) => void;
}): Promise<SessionData> {
  const channel = new Channel<FindHighlightsEvent>();
  if (params.onLog) {
    channel.onmessage = (event) => {
      if (event.type === "log") params.onLog!(event.message);
    };
  }

  return invoke<SessionData>("find_highlights", {
    url: params.url,
    numClips: params.numClips,
    subtitleLanguage: params.subtitleLanguage,
    ai: params.ai,
    userDirection: params.userDirection?.trim() || null,
    outputLanguage: params.outputLanguage || null,
    onEvent: channel,
  });
}
