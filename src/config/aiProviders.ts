export interface AIProviderPreset {
  key: string;
  name: string;
  baseUrl: string;
  description: string;
  docsUrl: string;
  /** Key-format hint; omit when the provider's format is unknown or varies. */
  apiKeyFormat?: string;
  requiresLoad: boolean;
  /** When set, the page shows a "get your API key" callout linking here. */
  signupUrl?: string;
}

export const AI_PROVIDER_PRESETS: AIProviderPreset[] = [
  {
    key: "ytclip",
    name: "⭐ YTClip AI",
    baseUrl: "https://ai-api.ytclip.org/v1",
    description: "YTClip AI - optimized for video content processing",
    docsUrl: "https://ytclip.org/api-keys",
    apiKeyFormat: "sk-*",
    requiresLoad: true,
    signupUrl: "https://ai.ytclip.org",
  },
  {
    key: "apismart",
    name: "⭐ ApiSmart",
    baseUrl: "https://gw.apismart.ai/v1",
    description: "ApiSmart - OpenAI-compatible multi-model gateway",
    docsUrl: "https://www.apismart.ai",
    requiresLoad: true,
    signupUrl: "https://www.apismart.ai",
  },
  {
    key: "openai",
    name: "🔴 OpenAI",
    baseUrl: "https://api.openai.com/v1",
    description: "OpenAI GPT models (GPT-4o, GPT-4, etc.)",
    docsUrl: "https://platform.openai.com/api-keys",
    apiKeyFormat: "sk-*",
    requiresLoad: true,
  },
  {
    key: "google",
    name: "🔵 Google Gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    description: "Google Generative AI (Gemini models)",
    docsUrl: "https://aistudio.google.com/app/apikey",
    apiKeyFormat: "AIza*",
    requiresLoad: false,
  },
  {
    key: "groq",
    name: "⚡ Groq",
    baseUrl: "https://api.groq.com/openai/v1",
    description: "Groq fast inference API",
    docsUrl: "https://console.groq.com/keys",
    apiKeyFormat: "gsk-*",
    requiresLoad: true,
  },
  {
    key: "custom",
    name: "⚙️ Custom / Local",
    baseUrl: "http://localhost:8000/v1",
    description: "Custom OpenAI-compatible endpoint (vLLM, Ollama, etc.)",
    docsUrl: "https://github.com/vllm-project/vllm",
    apiKeyFormat: "optional",
    requiresLoad: false,
  },
];

/** Fallback model suggestions for the model dropdown before a Load. */
export const FALLBACK_MODELS = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"];

export function presetForBaseUrl(baseUrl: string): AIProviderPreset {
  const match = AI_PROVIDER_PRESETS.find(
    (p) => p.key !== "custom" && baseUrl.includes(new URL(p.baseUrl).host)
  );
  return match ?? AI_PROVIDER_PRESETS[AI_PROVIDER_PRESETS.length - 1];
}

/** Host of a signup URL without a leading "www." — used as the link label. */
export function signupLabel(url: string): string {
  return new URL(url).host.replace(/^www\./, "");
}
