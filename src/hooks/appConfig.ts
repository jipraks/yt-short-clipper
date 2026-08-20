import { invoke } from "@tauri-apps/api/core";

export interface AIProviderSettings {
  baseUrl: string;
  apiKey: string;
  model: string;
  systemMessage?: string;
}

export interface WatermarkSettings {
  enabled: boolean;
  imagePath: string;
  positionX: number;
  positionY: number;
  opacity: number;
  scale: number;
}

export interface CreditWatermarkSettings {
  enabled: boolean;
  text: string;
  color: string;
  fontSize: number;
  opacity: number;
  positionX: number;
  positionY: number;
}

export interface HookStyleSettings {
  fontName: string;
  fontPath: string;
  fontSize: number;
  fontColor: string;
  bgColor: string;
  cornerRadius: number;
  positionX: number;
  positionY: number;
  durationSeconds: number;
}

export interface ReplizSettings {
  accessKey: string;
  secretKey: string;
}

export interface AppConfig {
  /** Single AI provider shared by highlight finding and title generation. */
  ai: AIProviderSettings;
  gpuAcceleration: {
    enabled: boolean;
  };
  watermark: WatermarkSettings;
  creditWatermark: CreditWatermarkSettings;
  hookStyle: HookStyleSettings;
  repliz: ReplizSettings;
  /** Stable per-install UUID, generated on first run. Persists across updates. */
  installationId: string;
}

export const DEFAULT_CONFIG: AppConfig = {
  ai: {
    baseUrl: "https://ai-api.ytclip.org/v1",
    apiKey: "",
    model: "",
    systemMessage: "",
  },
  gpuAcceleration: {
    enabled: false,
  },
  watermark: {
    enabled: false,
    imagePath: "",
    positionX: 0.85,
    positionY: 0.05,
    opacity: 0.8,
    scale: 0.15,
  },
  creditWatermark: {
    enabled: false,
    text: "Source: {channel}",
    color: "#FFFFFF",
    fontSize: 24,
    opacity: 0.7,
    positionX: 0.03,
    positionY: 0.92,
  },
  hookStyle: {
    fontName: "Arial",
    fontPath: "",
    fontSize: 0.054,
    fontColor: "#FFD700",
    bgColor: "#FFFFFF",
    cornerRadius: 0,
    positionX: 0.5,
    positionY: 0.333,
    durationSeconds: 5,
  },
  repliz: {
    accessKey: "",
    secretKey: "",
  },
  installationId: "",
};

export async function loadAppConfig(): Promise<AppConfig> {
  const config = await invoke<Partial<AppConfig>>("load_app_config");
  return mergeConfig(config);
}

export async function saveAppConfig(config: AppConfig): Promise<AppConfig> {
  const saved = await invoke<Partial<AppConfig>>("save_app_config", { config });
  return mergeConfig(saved);
}

export async function listAIModels(apiKey: string, baseUrl: string): Promise<string[]> {
  return invoke<string[]>("list_ai_models", { apiKey, baseUrl });
}

export interface GpuInfo {
  type: string | null;
  name: string;
  available: boolean;
}

export interface GpuEncoder {
  name: string | null;
  preset: string | null;
  available: boolean;
  reason: string;
}

export interface GpuDetection {
  gpu: GpuInfo;
  encoder: GpuEncoder;
}

export async function detectGpu(): Promise<GpuDetection> {
  return invoke<GpuDetection>("detect_gpu");
}

export interface FontInfo {
  name: string;
  path: string;
}

export async function listHookFonts(): Promise<FontInfo[]> {
  return invoke<FontInfo[]>("list_hook_fonts");
}

export async function readFontAsBase64(path: string): Promise<string> {
  return invoke<string>("read_file_as_base64", { path });
}

export interface SavedWatermark {
  path: string;
  dataUrl: string;
}

export async function saveWatermark(
  fileName: string,
  bytes: Uint8Array
): Promise<SavedWatermark> {
  return invoke<SavedWatermark>("save_watermark", {
    fileName,
    bytes: Array.from(bytes),
  });
}

export async function readWatermark(path: string): Promise<string> {
  return invoke<string>("read_watermark", { path });
}

function mergeConfig(config: Partial<AppConfig> | undefined): AppConfig {
  // Migrate from the legacy per-task shape (aiProviders.highlightFinder) so
  // users who already configured a key don't have to re-enter it.
  const legacyAi = (config as { aiProviders?: { highlightFinder?: Partial<AIProviderSettings> } } | undefined)
    ?.aiProviders?.highlightFinder;
  return {
    ai: {
      ...DEFAULT_CONFIG.ai,
      ...legacyAi,
      ...config?.ai,
    },
    gpuAcceleration: {
      ...DEFAULT_CONFIG.gpuAcceleration,
      ...config?.gpuAcceleration,
    },
    watermark: {
      ...DEFAULT_CONFIG.watermark,
      ...config?.watermark,
    },
    creditWatermark: {
      ...DEFAULT_CONFIG.creditWatermark,
      ...config?.creditWatermark,
    },
    hookStyle: {
      ...DEFAULT_CONFIG.hookStyle,
      ...config?.hookStyle,
    },
    repliz: {
      ...DEFAULT_CONFIG.repliz,
      ...config?.repliz,
    },
    installationId: config?.installationId ?? DEFAULT_CONFIG.installationId,
  };
}
