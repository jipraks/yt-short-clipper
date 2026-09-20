import { invoke } from "@tauri-apps/api/core";

/**
 * Which AI the app infers with.
 *
 * `inapp` uses the device account: the balance is topped up with QRIS inside
 * the app and the LiteLLM key never reaches this process — Rust resolves it.
 * `custom` is the user's own OpenAI-compatible endpoint and key, including the
 * separate wallet at ai.ytclip.org.
 */
export type AISource = "inapp" | "custom";

export interface CustomAISettings {
  baseUrl: string;
  apiKey: string;
  model: string;
}

export interface InappAISettings {
  model: string;
}

export interface AISettings {
  source: AISource;
  custom: CustomAISettings;
  inapp: InappAISettings;
  /**
   * Highlight-finder prompt override. Shared by both sources deliberately — it
   * is a prompt, not a credential, and re-typing it on every switch would be
   * the kind of small cruelty nobody notices until they have done it twice.
   */
  systemMessage: string;
}

export interface AccountSettings {
  /**
   * When the user confirmed they had saved their account key, ISO 8601.
   *
   * Null blocks the first top-up: the server keeps no recovery path, so money
   * must not go in before the only key to it is somewhere safe.
   */
  keyBackupConfirmedAt: string | null;
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

/**
 * Slack added around every AI-chosen clip range, in seconds.
 *
 * The model copies its timestamps from subtitle cue markers, and a YouTube ASR
 * cue boundary is a rolling-window artifact rather than a sentence boundary —
 * the cue end is simply where the next cue begins, so the speaker is usually
 * still mid-sentence there. Padding buys the clip back its full thought.
 */
export interface ClipPaddingSettings {
  /** Seconds kept before the chosen start. */
  leadIn: number;
  /** Seconds kept after the chosen end. */
  tailOut: number;
}

/** Ceiling enforced in the UI and again in the Python worker. */
export const MAX_CLIP_PADDING = 15;

export interface AppConfig {
  /** Single AI provider shared by highlight finding and title generation. */
  ai: AISettings;
  account: AccountSettings;
  gpuAcceleration: {
    enabled: boolean;
  };
  watermark: WatermarkSettings;
  creditWatermark: CreditWatermarkSettings;
  hookStyle: HookStyleSettings;
  clipPadding: ClipPaddingSettings;
  repliz: ReplizSettings;
  /** Stable per-install UUID, generated on first run. Persists across updates. */
  installationId: string;
}

export const DEFAULT_CONFIG: AppConfig = {
  ai: {
    source: "inapp",
    custom: {
      baseUrl: "https://ai-api.ytclip.org/v1",
      apiKey: "",
      model: "",
    },
    inapp: {
      model: "",
    },
    systemMessage: "",
  },
  account: {
    keyBackupConfirmedAt: null,
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
  clipPadding: {
    leadIn: 1.5,
    tailOut: 2.5,
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

/** The flat `{ baseUrl, apiKey, model }` shape that predates the source split. */
interface LegacyFlatAI {
  baseUrl?: string;
  apiKey?: string;
  model?: string;
  systemMessage?: string;
}

/**
 * Reads whatever shape is on disk into the current one.
 *
 * Two migrations live here. The older is `aiProviders.highlightFinder`, from
 * when every task carried its own provider. The newer is the flat `ai` block
 * that existed before in-app accounts — and its rule is the one that matters:
 * a user who already typed a key keeps `custom`, because flipping a working
 * install into a mode that demands activation is how an update becomes a
 * support ticket. Only a genuinely empty config lands on `inapp`.
 */
function mergeAI(raw: unknown, legacy: LegacyFlatAI | undefined): AISettings {
  const value = (raw ?? {}) as Partial<AISettings> & LegacyFlatAI;

  if (value.source === "inapp" || value.source === "custom") {
    return {
      source: value.source,
      custom: { ...DEFAULT_CONFIG.ai.custom, ...value.custom },
      inapp: { ...DEFAULT_CONFIG.ai.inapp, ...value.inapp },
      systemMessage: value.systemMessage ?? DEFAULT_CONFIG.ai.systemMessage,
    };
  }

  const flat: LegacyFlatAI = { ...legacy, ...value };
  const hasKey = (flat.apiKey ?? "").trim() !== "";

  return {
    source: hasKey ? "custom" : "inapp",
    custom: {
      baseUrl: flat.baseUrl || DEFAULT_CONFIG.ai.custom.baseUrl,
      apiKey: flat.apiKey ?? "",
      model: flat.model ?? "",
    },
    inapp: { ...DEFAULT_CONFIG.ai.inapp },
    systemMessage: flat.systemMessage ?? DEFAULT_CONFIG.ai.systemMessage,
  };
}

function mergeConfig(config: Partial<AppConfig> | undefined): AppConfig {
  const legacyAi = (config as { aiProviders?: { highlightFinder?: LegacyFlatAI } } | undefined)
    ?.aiProviders?.highlightFinder;

  return {
    ai: mergeAI(config?.ai, legacyAi),
    account: {
      ...DEFAULT_CONFIG.account,
      ...config?.account,
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
    clipPadding: {
      ...DEFAULT_CONFIG.clipPadding,
      ...config?.clipPadding,
    },
    repliz: {
      ...DEFAULT_CONFIG.repliz,
      ...config?.repliz,
    },
    installationId: config?.installationId ?? DEFAULT_CONFIG.installationId,
  };
}
