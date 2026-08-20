import { useEffect, useMemo, useState } from "react";
import { ExternalLink, KeyRound, Loader2, Save, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  AI_PROVIDER_PRESETS,
  FALLBACK_MODELS,
  presetForBaseUrl,
  signupLabel,
} from "@/config/aiProviders";
import { listAIModels, type AIProviderSettings } from "@/hooks/appConfig";
import { useConfigStore } from "@/stores/configStore";
import { open as openUrl } from "@tauri-apps/plugin-shell";

export function AIModelsPage() {
  const { config, loaded, load, setAI } = useConfigStore();

  useEffect(() => {
    load();
  }, [load]);

  if (!loaded) {
    return (
      <div className="flex items-center justify-center py-20 text-[var(--color-text-muted)]">
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        Loading AI settings...
      </div>
    );
  }

  return (
    <AIProviderEditor
      settings={config.ai}
      onSave={async (settings) => {
        await setAI(settings);
        toast.success("AI provider saved");
      }}
    />
  );
}

interface AIProviderEditorProps {
  settings: AIProviderSettings;
  onSave: (settings: AIProviderSettings) => Promise<void>;
}

function AIProviderEditor({ settings, onSave }: AIProviderEditorProps) {
  const initialPreset = presetForBaseUrl(settings.baseUrl);

  const [providerKey, setProviderKey] = useState(initialPreset.key);
  const [baseUrl, setBaseUrl] = useState(settings.baseUrl || initialPreset.baseUrl);
  const [apiKey, setApiKey] = useState(settings.apiKey || "");
  const [model, setModel] = useState(settings.model || "");
  const [systemMessage, setSystemMessage] = useState(settings.systemMessage || "");
  const [models, setModels] = useState<string[]>(() =>
    settings.model && !FALLBACK_MODELS.includes(settings.model)
      ? [settings.model, ...FALLBACK_MODELS]
      : FALLBACK_MODELS
  );
  const [loadingModels, setLoadingModels] = useState(false);
  const [saving, setSaving] = useState(false);

  const selectedPreset = useMemo(
    () => AI_PROVIDER_PRESETS.find((p) => p.key === providerKey) ?? AI_PROVIDER_PRESETS[0],
    [providerKey]
  );

  const isCustom = providerKey === "custom";
  const signupUrl = selectedPreset.signupUrl;

  const handleProviderChange = (value: string) => {
    const preset = AI_PROVIDER_PRESETS.find((p) => p.key === value) ?? AI_PROVIDER_PRESETS[0];
    setProviderKey(preset.key);
    setBaseUrl(preset.baseUrl);
  };

  const handleLoadModels = async () => {
    if (!apiKey.trim()) {
      toast.error("API key is required");
      return;
    }

    setLoadingModels(true);
    try {
      const loaded = await listAIModels(apiKey, baseUrl);
      setModels(loaded);
      if (loaded.length > 0 && !loaded.includes(model)) {
        setModel(loaded[0]);
      }
      toast.success(`Loaded ${loaded.length} models`);
    } catch (err) {
      console.error("Failed to load models", err);
      const detail = err instanceof Error ? err.message : String(err);
      toast.error("Failed to load models");
      setModels((prev) => (prev.length ? prev : FALLBACK_MODELS));
      alert(detail);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey.trim()) {
      toast.error("API key is required");
      return;
    }
    if (!model.trim()) {
      toast.error("Model is required");
      return;
    }

    setSaving(true);
    try {
      await onSave({ baseUrl, apiKey, model, systemMessage });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
          AI Model
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          One AI provider for the whole app — used for both finding highlights and
          generating titles. Configure it once.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[var(--color-accent)]" />
            Provider Type
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <select
            value={providerKey}
            onChange={(e) => handleProviderChange(e.target.value)}
            className="w-full h-10 px-3 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)]"
          >
            {AI_PROVIDER_PRESETS.map((provider) => (
              <option key={provider.key} value={provider.key}>
                {provider.name}
              </option>
            ))}
          </select>

          <p className="text-xs text-[var(--color-text-muted)]">
            {selectedPreset.description}
            {selectedPreset.apiKeyFormat
              ? ` · API key format: ${selectedPreset.apiKeyFormat}`
              : ""}
          </p>

          {signupUrl && (
            <div className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--color-accent-light)] border border-[var(--color-accent)]/30">
              <Sparkles className="w-4 h-4 text-[var(--color-accent)] shrink-0 mt-0.5" />
              <div className="text-xs text-[var(--color-text-secondary)] space-y-1">
                <p>
                  Don't have an account yet? Get your API key at{" "}
                  <button
                    type="button"
                    onClick={() => openUrl(signupUrl)}
                    className="inline-flex items-center gap-1 text-[var(--color-accent)] font-medium hover:underline cursor-pointer"
                  >
                    {signupLabel(signupUrl)}
                    <ExternalLink className="w-3 h-3" />
                  </button>
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-[var(--color-accent)]" />
            API Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isCustom ? (
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                Base URL
              </label>
              <Input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
            </div>
          ) : (
            <div className="space-y-1">
              <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                Base URL
              </label>
              <div className="text-sm px-3 py-2 rounded-[var(--radius-sm)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-light)] text-[var(--color-text-muted)]">
                {baseUrl}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)]">
              API Key
            </label>
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={selectedPreset.apiKeyFormat ?? "Your API key"}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)]">
              Model
            </label>
            <div className="flex gap-2">
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="flex-1 h-10 px-3 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)]"
              >
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <Button variant="outline" onClick={handleLoadModels} disabled={loadingModels}>
                {loadingModels ? <Loader2 className="w-4 h-4 animate-spin" /> : "Load"}
              </Button>
            </div>
            <Input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Or type a model manually"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)]">
              System Message
              <span className="ml-1 font-normal text-[var(--color-text-muted)]">
                (highlight finder only)
              </span>
            </label>
            <textarea
              value={systemMessage}
              onChange={(e) => setSystemMessage(e.target.value)}
              placeholder="Optional custom instructions for highlight detection"
              className="w-full min-h-[180px] px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] resize-y"
            />
            <p className="text-xs text-[var(--color-text-muted)]">
              Available placeholders: {"{num_clips}"}, {"{video_context}"},{" "}
              {"{transcript}"}, {"{user_direction}"}. Leave {"{user_direction}"} out and
              any direction typed on the Create page is appended at the end instead.
            </p>
          </div>
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving} className="w-full h-12 gap-2">
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        Save AI Provider
      </Button>
    </div>
  );
}
