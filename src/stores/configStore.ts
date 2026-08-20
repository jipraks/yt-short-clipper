import { create } from "zustand";
import {
  loadAppConfig,
  saveAppConfig,
  DEFAULT_CONFIG,
  type AppConfig,
  type AIProviderSettings,
  type WatermarkSettings,
  type CreditWatermarkSettings,
  type HookStyleSettings,
  type ReplizSettings,
} from "@/hooks/appConfig";

interface ConfigState {
  config: AppConfig;
  loaded: boolean;
  load: () => Promise<void>;
  setAI: (settings: AIProviderSettings) => Promise<void>;
  setGpuAcceleration: (enabled: boolean) => Promise<void>;
  setWatermark: (watermark: WatermarkSettings) => Promise<void>;
  setCreditWatermark: (creditWatermark: CreditWatermarkSettings) => Promise<void>;
  setHookStyle: (hookStyle: HookStyleSettings) => Promise<void>;
  setRepliz: (repliz: ReplizSettings) => Promise<void>;
  isAIConfigured: () => boolean;
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

  setAI: async (settings) => {
    const next: AppConfig = {
      ...get().config,
      ai: settings,
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
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

  setRepliz: async (repliz) => {
    const next: AppConfig = {
      ...get().config,
      repliz,
    };
    const saved = await saveAppConfig(next);
    set({ config: saved });
  },

  isAIConfigured: () => {
    const p = get().config.ai;
    return !!p && p.apiKey.trim() !== "" && p.model.trim() !== "";
  },
}));
