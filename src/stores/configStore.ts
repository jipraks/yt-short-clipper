import { create } from "zustand";
import {
  loadAppConfig,
  saveAppConfig,
  DEFAULT_CONFIG,
  type AppConfig,
  type AISource,
  type CustomAISettings,
  type WatermarkSettings,
  type CreditWatermarkSettings,
  type HookStyleSettings,
  type ClipPaddingSettings,
  type ReplizSettings,
} from "@/hooks/appConfig";

interface ConfigState {
  config: AppConfig;
  loaded: boolean;
  load: () => Promise<void>;
  setAISource: (source: AISource) => Promise<void>;
  setCustomAI: (custom: CustomAISettings) => Promise<void>;
  setInappModel: (model: string) => Promise<void>;
  setSystemMessage: (systemMessage: string) => Promise<void>;
  confirmKeyBackup: () => Promise<void>;
  setGpuAcceleration: (enabled: boolean) => Promise<void>;
  setWatermark: (watermark: WatermarkSettings) => Promise<void>;
  setCreditWatermark: (creditWatermark: CreditWatermarkSettings) => Promise<void>;
  setHookStyle: (hookStyle: HookStyleSettings) => Promise<void>;
  setClipPadding: (clipPadding: ClipPaddingSettings) => Promise<void>;
  setRepliz: (repliz: ReplizSettings) => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  config: DEFAULT_CONFIG,
  loaded: false,

  load: async () => {
    try {
      const config = await loadAppConfig();
      set({ config, loaded: true });
    } catch {
      set({ config: DEFAULT_CONFIG, loaded: true });
    }
  },

  setAISource: async (source) => {
    const current = get().config;
    const next: AppConfig = {
      ...current,
      ai: { ...current.ai, source },
    };
    set({ config: await saveAppConfig(next) });
  },

  setCustomAI: async (custom) => {
    const current = get().config;
    const next: AppConfig = {
      ...current,
      ai: { ...current.ai, custom },
    };
    set({ config: await saveAppConfig(next) });
  },

  setInappModel: async (model) => {
    const current = get().config;
    const next: AppConfig = {
      ...current,
      ai: { ...current.ai, inapp: { ...current.ai.inapp, model } },
    };
    set({ config: await saveAppConfig(next) });
  },

  setSystemMessage: async (systemMessage) => {
    const current = get().config;
    const next: AppConfig = {
      ...current,
      ai: { ...current.ai, systemMessage },
    };
    set({ config: await saveAppConfig(next) });
  },

  confirmKeyBackup: async () => {
    const current = get().config;
    const next: AppConfig = {
      ...current,
      account: { keyBackupConfirmedAt: new Date().toISOString() },
    };
    set({ config: await saveAppConfig(next) });
  },

  setGpuAcceleration: async (enabled) => {
    const next: AppConfig = {
      ...get().config,
      gpuAcceleration: { enabled },
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
  },

  setWatermark: async (watermark) => {
    const next: AppConfig = {
      ...get().config,
      watermark,
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
  },

  setCreditWatermark: async (creditWatermark) => {
    const next: AppConfig = {
      ...get().config,
      creditWatermark,
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
  },

  setHookStyle: async (hookStyle) => {
    const next: AppConfig = {
      ...get().config,
      hookStyle,
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
  },

  setClipPadding: async (clipPadding) => {
    const next: AppConfig = {
      ...get().config,
      clipPadding,
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
  },

  setRepliz: async (repliz) => {
    const next: AppConfig = {
      ...get().config,
      repliz,
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
  },
}));
