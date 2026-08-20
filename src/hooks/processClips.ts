import { invoke, Channel } from "@tauri-apps/api/core";

export type ReframeMode = "face" | "centered";
export type CenteredBackground = "black" | "blurred";

export interface ProcessOptions {
  addCaptions: boolean;
  addHook: boolean;
  addWatermark: boolean;
  addCreditWatermark: boolean;
  reframeMode: ReframeMode;
  centeredBackground: CenteredBackground;
}

export type ProcessClipsEvent = { type: "log"; message: string };

export async function processClips(params: {
  url: string;
  highlights: unknown[];
  sessionDir: string;
  options: ProcessOptions;
  ai: {
    api_key: string;
    base_url: string;
    model: string;
    system_message?: string;
    temperature?: number;
    hook_style?: {
      font_name: string;
      font_path: string;
      font_size: number;
      font_color: string;
      bg_color: string;
      corner_radius: number;
      position_x: number;
      position_y: number;
      duration_seconds: number;
    };
    watermark?: {
      image_path: string;
      position_x: number;
      position_y: number;
      opacity: number;
      scale: number;
    };
    credit_watermark?: {
      text: string;
      color: string;
      font_size: number;
      opacity: number;
      position_x: number;
      position_y: number;
    };
  };
  onLog?: (message: string) => void;
}): Promise<unknown> {
  const channel = new Channel<ProcessClipsEvent>();
  if (params.onLog) {
    channel.onmessage = (event) => {
      if (event.type === "log") params.onLog!(event.message);
    };
  }

  return invoke("process_clips", {
    url: params.url,
    highlights: params.highlights,
    sessionDir: params.sessionDir,
    options: params.options,
    ai: params.ai,
    onEvent: channel,
  });
}
