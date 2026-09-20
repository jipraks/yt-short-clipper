import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Coins,
  ExternalLink,
  KeyRound,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { AccountKeyDialog } from "@/components/AccountKeyDialog";
import { TopupDialog } from "@/components/TopupDialog";
import {
  AI_PROVIDER_PRESETS,
  FALLBACK_MODELS,
  presetForBaseUrl,
  signupLabel,
} from "@/config/aiProviders";
import {
  errorCode,
  errorMessage,
  fetchModels,
  fetchUsage,
  jakartaDate,
  type CatalogModel,
  type UsageLog,
} from "@/hooks/account";
import { listAIModels, type CustomAISettings } from "@/hooks/appConfig";
import { useConfigStore } from "@/stores/configStore";
import { ensureDefaultModel, inappSupported, useAccountStore } from "@/stores/accountStore";
import { formatSpendUsd, formatUsd } from "@/utils/format";
import { cn } from "@/lib/utils";
import { open as openUrl } from "@tauri-apps/plugin-shell";

export function AIModelsPage() {
  const { config, loaded, load, setAISource } = useConfigStore();

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

  const source = config.ai.source;

  // Writing config can fail — a locked file, a full disk — and a switch that
  // silently does nothing is worse than one that says why.
  const switchSource = (next: typeof source) => {
    setAISource(next).catch((err) => toast.error(errorMessage(err)));
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[var(--color-text-primary)]">AI Model</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          One AI provider for the whole app — used for finding highlights and for
          generating titles.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <SourceCard
          active={source === "inapp"}
          icon={Coins}
          title="In-app AI"
          description="Top up with QRIS inside the app. No account, no API key to paste."
          onClick={() => switchSource("inapp")}
        />
        <SourceCard
          active={source === "custom"}
          icon={KeyRound}
          title="Own API key"
          description="Any OpenAI-compatible endpoint, including your balance at ai.ytclip.org."
          onClick={() => switchSource("custom")}
        />
      </div>

      {source === "inapp" ? <InappPanel /> : <CustomPanel />}

      <SystemMessageCard />
    </div>
  );
}

function SourceCard({
  active,
  icon: Icon,
  title,
  description,
  onClick,
}: {
  active: boolean;
  icon: typeof Coins;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "text-left p-4 rounded-[var(--radius)] border transition-all duration-200 cursor-pointer",
        active
          ? "border-[var(--color-accent)] bg-[var(--color-accent-light)]"
          : "border-[var(--color-border-light)] bg-[var(--color-bg-card)] hover:bg-[var(--color-bg-hover)]"
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon
          className={cn(
            "w-4 h-4",
            active ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]"
          )}
        />
        <span
          className={cn(
            "text-sm font-semibold",
            active ? "text-[var(--color-accent)]" : "text-[var(--color-text-primary)]"
          )}
        >
          {title}
        </span>
      </div>
      <p className="text-xs text-[var(--color-text-secondary)]">{description}</p>
    </button>
  );
}

// ---------------------------------------------------------------------------
// In-app
// ---------------------------------------------------------------------------

function InappPanel() {
  const { activated, account, appInfo, busy, activate, refresh } = useAccountStore();
  const supported = inappSupported(appInfo);

  const [dialog, setDialog] = useState<"topup" | "export" | "restore" | null>(null);

  const handleActivate = async () => {
    try {
      await activate();
      toast.success("In-app AI activated");
      // Catalogue unreachable is survivable — the picker below still offers it.
      await ensureDefaultModel().catch(() => undefined);
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  if (!supported) {
    return (
      <Card>
        <CardContent className="flex items-start gap-3 py-2">
          <AlertTriangle className="w-5 h-5 text-[var(--color-warning)] shrink-0 mt-0.5" />
          <div className="space-y-2">
            <p className="text-sm text-[var(--color-text-primary)] font-medium">
              This version is too old for in-app AI
            </p>
            <p className="text-xs text-[var(--color-text-secondary)]">
              Update to v{appInfo?.latestVersion} to use the in-app balance. The
              rest of the app keeps working, and your own API key still works on
              this version.
            </p>
            {appInfo?.downloadUrl && (
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => openUrl(appInfo.downloadUrl)}
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Download the update
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!activated) {
    return (
      <>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[var(--color-accent)]" />
              In-app AI is not set up yet
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">
              The wallet for this installation normally sets itself up when the
              app starts — no email, no password, no website. That did not go
              through, usually because there was no connection. It will try
              again next launch, or you can retry now.
            </p>

            <div className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--color-warning-bg)] border border-[var(--color-warning)]/30">
              <ShieldCheck className="w-4 h-4 text-[var(--color-warning)] shrink-0 mt-0.5" />
              <p className="text-xs text-[var(--color-text-secondary)]">
                The wallet is held by a key stored on this computer. Export that
                key and keep it safe — it is the only way to reach the balance
                from another machine, and nobody can restore it for you.
              </p>
            </div>

            <div className="flex gap-2">
              <Button onClick={handleActivate} disabled={busy} className="flex-1 gap-2">
                {busy ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                Retry activation
              </Button>
              <Button
                variant="outline"
                onClick={() => setDialog("restore")}
                className="gap-2"
              >
                <Upload className="w-4 h-4" />
                Restore
              </Button>
            </div>

            <p className="text-xs text-[var(--color-text-muted)]">
              Already have a balance at ai.ytclip.org? That is a separate wallet
              — switch to "Own API key" and paste its key there.
            </p>
          </CardContent>
        </Card>

        {dialog === "restore" && (
          <AccountKeyDialog mode="restore" onClose={() => setDialog(null)} />
        )}
      </>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Coins className="w-5 h-5 text-[var(--color-accent)]" />
              Balance
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={refresh} className="gap-1.5">
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {account?.blocked && (
            <div className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] border border-[var(--color-error)]/30">
              <AlertTriangle className="w-4 h-4 text-[var(--color-error)] shrink-0 mt-0.5" />
              <p className="text-xs text-[var(--color-text-secondary)]">
                {account.blockedReason ??
                  "This account has been disabled. Contact support@ytclip.org."}
              </p>
            </div>
          )}

          <div className="flex items-end justify-between">
            <div>
              <p className="text-3xl font-bold text-[var(--color-text-primary)]">
                {account ? formatUsd(account.balanceUsd) : "—"}
              </p>
              {account && (
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  Topped up {formatUsd(account.toppedUpUsd)} · spent{" "}
                  {formatUsd(account.spentUsd)}
                </p>
              )}
            </div>
            <Button onClick={() => setDialog("topup")} className="gap-2">
              <Plus className="w-4 h-4" />
              Top Up
            </Button>
          </div>

          {account && (
            <div className="text-xs text-[var(--color-text-muted)] space-y-1 pt-1 border-t border-[var(--color-border-light)]">
              <p className="pt-2">
                Account ID: <span className="font-mono">{account.accountId}</span>
              </p>
              <p>
                Tier: {account.membership.tier}
                {account.membership.tier !== "GOLD" &&
                  ` · ${formatUsd(account.membership.remainingUsd)} more to reach GOLD`}
              </p>
              {account.membership.groupUrl && (
                <button
                  onClick={() => openUrl(account.membership.groupUrl!)}
                  className="inline-flex items-center gap-1 text-[var(--color-accent)] hover:underline cursor-pointer"
                >
                  Join the VIP group
                  <ExternalLink className="w-3 h-3" />
                </button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <InappModelCard />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="w-5 h-5 text-[var(--color-accent)]" />
            Account Key
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-[var(--color-text-secondary)]">
            Your balance lives behind one key held on this computer. Export it and
            keep it somewhere private — it is the only way to reach the balance
            after a reinstall or on another machine.
          </p>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setDialog("export")} className="gap-2">
              <KeyRound className="w-4 h-4" />
              Export key
            </Button>
            <Button variant="outline" onClick={() => setDialog("restore")} className="gap-2">
              <Upload className="w-4 h-4" />
              Restore another
            </Button>
          </div>
        </CardContent>
      </Card>

      <UsageCard />

      {dialog === "topup" && <TopupDialog onClose={() => setDialog(null)} />}
      {dialog === "export" && (
        <AccountKeyDialog mode="export" onClose={() => setDialog(null)} />
      )}
      {dialog === "restore" && (
        <AccountKeyDialog mode="restore" onClose={() => setDialog(null)} />
      )}
    </>
  );
}

function InappModelCard() {
  const model = useConfigStore((s) => s.config.ai.inapp.model);
  const setInappModel = useConfigStore((s) => s.setInappModel);

  const [models, setModels] = useState<CatalogModel[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchModels()
      .then(({ data }) => setModels(data))
      .catch((err) => toast.error(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  const chatModels = useMemo(
    () => (models ?? []).filter((m) => m.mode === "chat" || m.mode === "unknown"),
    [models]
  );
  const selected = chatModels.find((m) => m.name === model);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-[var(--color-accent)]" />
          Model
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading the catalogue...
          </div>
        ) : (
          <>
            <select
              value={model}
              onChange={(e) =>
                setInappModel(e.target.value).catch((err) =>
                  toast.error(errorMessage(err))
                )
              }
              className="w-full h-10 px-3 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)]"
            >
              {!model && <option value="">Choose a model</option>}
              {chatModels.map((m) => (
                <option key={m.id} value={m.name}>
                  {m.name}
                </option>
              ))}
              {model && !selected && <option value={model}>{model}</option>}
            </select>

            {selected && (
              <p className="text-xs text-[var(--color-text-muted)]">
                {selected.provider} ·{" "}
                {selected.inputCostPerToken !== null
                  ? `${formatUsd(selected.inputCostPerToken * 1_000_000)} in`
                  : "price unavailable"}
                {selected.outputCostPerToken !== null &&
                  ` / ${formatUsd(selected.outputCostPerToken * 1_000_000)} out per 1M tokens`}
                {selected.maxInputTokens
                  ? ` · ${(selected.maxInputTokens / 1000).toFixed(0)}k context`
                  : ""}
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function UsageCard() {
  const [rows, setRows] = useState<UsageLog[] | null>(null);
  const [empty, setEmpty] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsage(jakartaDate(-6), jakartaDate(), 1, 10)
      .then((page) => setRows(page.data))
      .catch((err) => {
        // An account that has never inferred is an empty state, not a failure.
        if (errorCode(err) === "NOT_PROVISIONED") setEmpty(true);
        else setRows([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const total = (rows ?? []).reduce((sum, row) => sum + row.spendUsd, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage — last 7 days</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading...
          </div>
        ) : empty || !rows?.length ? (
          <p className="text-sm text-[var(--color-text-muted)]">
            Nothing yet. Requests show up here with what each one cost.
          </p>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-[var(--color-text-secondary)]">
              {rows.length} recent requests · {formatSpendUsd(total)}
            </p>
            <div className="divide-y divide-[var(--color-border-light)]">
              {rows.map((row) => (
                <div
                  key={row.requestId}
                  className="flex items-center justify-between py-1.5 text-xs"
                >
                  <div className="min-w-0">
                    <p className="text-[var(--color-text-primary)] truncate">
                      {row.model}
                    </p>
                    <p className="text-[var(--color-text-muted)]">
                      {new Date(row.startedAt).toLocaleString()} ·{" "}
                      {row.totalTokens.toLocaleString()} tokens
                    </p>
                  </div>
                  <span
                    className={
                      row.status === "failure"
                        ? "text-[var(--color-error)] shrink-0 ml-3"
                        : "text-[var(--color-text-secondary)] shrink-0 ml-3"
                    }
                  >
                    {row.status === "failure" ? "failed" : formatSpendUsd(row.spendUsd)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Custom provider
// ---------------------------------------------------------------------------

function CustomPanel() {
  const settings = useConfigStore((s) => s.config.ai.custom);
  const setCustomAI = useConfigStore((s) => s.setCustomAI);

  const initialPreset = presetForBaseUrl(settings.baseUrl);
  const [providerKey, setProviderKey] = useState(initialPreset.key);
  const [baseUrl, setBaseUrl] = useState(settings.baseUrl || initialPreset.baseUrl);
  const [apiKey, setApiKey] = useState(settings.apiKey || "");
  const [model, setModel] = useState(settings.model || "");
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

  const isCustomEndpoint = providerKey === "custom";
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
      toast.error(`Failed to load models: ${errorMessage(err)}`);
      setModels((prev) => (prev.length ? prev : FALLBACK_MODELS));
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
      const next: CustomAISettings = { baseUrl, apiKey, model };
      await setCustomAI(next);
      toast.success("AI provider saved");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
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
          {isCustomEndpoint ? (
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
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving} className="w-full h-12 gap-2">
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        Save AI Provider
      </Button>
    </>
  );
}

/**
 * Shared by both sources — it is a prompt, not a credential, so switching
 * provider should not cost the user the instructions they tuned.
 */
function SystemMessageCard() {
  const stored = useConfigStore((s) => s.config.ai.systemMessage);
  const setSystemMessage = useConfigStore((s) => s.setSystemMessage);
  const [value, setValue] = useState(stored);
  const [saving, setSaving] = useState(false);

  useEffect(() => setValue(stored), [stored]);

  const dirty = value !== stored;

  const save = async () => {
    setSaving(true);
    try {
      await setSystemMessage(value);
      toast.success("System message saved");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          System Message
          <span className="ml-2 text-sm font-normal text-[var(--color-text-muted)]">
            (highlight finder only)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Optional custom instructions for highlight detection"
          className="w-full min-h-[180px] px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] resize-y"
        />
        <p className="text-xs text-[var(--color-text-muted)]">
          Available placeholders: {"{num_clips}"}, {"{video_context}"},{" "}
          {"{transcript}"}, {"{user_direction}"}. Leave {"{user_direction}"} out and
          any direction typed on the Create page is appended at the end instead.
        </p>
        {dirty && (
          <Button onClick={save} disabled={saving} variant="outline" className="gap-2">
            {saving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save system message
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
