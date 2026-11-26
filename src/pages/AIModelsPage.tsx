import { IS_STORE_BUILD } from "@/config/distribution";
import { useEffect, useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Check, Copy, ExternalLink, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Combobox, type ComboboxGroup } from "@/components/ui/combobox";
import { AccountKeyDialog } from "@/components/AccountKeyDialog";
import { TopupDialog } from "@/components/TopupDialog";
import {
  AI_PROVIDER_PRESETS,
  FALLBACK_MODELS,
  presetForBaseUrl,
  signupLabel,
  type AIProviderPreset,
} from "@/config/aiProviders";
import { errorCode, errorMessage, fetchUsage, jakartaDate, type Membership, type UsageLog } from "@/hooks/account";
import { listAIModels, type CustomAISettings } from "@/hooks/appConfig";
import { useConfigStore } from "@/stores/configStore";
import { chatModels, ensureDefaultModel, inappSupported, useAccountStore } from "@/stores/accountStore";
import { formatIdr, formatSpendUsd, formatUsd } from "@/utils/format";
import { cn } from "@/lib/utils";
import { open as openUrl } from "@tauri-apps/plugin-shell";

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]";

const pickerTrigger = cn(
  "inline-flex h-11 w-full items-center justify-between gap-1.5 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] px-3 text-sm text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-bg-hover)] disabled:opacity-60",
  focusRing,
);

const textLink = cn(
  "inline-flex min-h-9 items-center gap-1 rounded-[var(--radius-sm)] font-medium text-[var(--color-accent)] hover:underline cursor-pointer",
  focusRing,
);

type AISource = "inapp" | "custom";

export function AIModelsPage() {
  const { t } = useTranslation();
  const { config, loaded, load, setAISource } = useConfigStore();

  useEffect(() => {
    load();
  }, [load]);

  if (!loaded) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-[var(--color-text-muted)]">
        <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
        {t("aiPage.loading")}
      </div>
    );
  }

  const source = config.ai.source;

  // Writing config can fail (a locked file, a full disk), and a switch that
  // silently does nothing is worse than one that says why.
  const switchSource = (next: AISource) => {
    if (next === source) return;
    setAISource(next).catch((err) => toast.error(t("aiPage.saveFailed", { reason: errorMessage(err) })));
  };

  return (
    <div className="mx-auto max-w-2xl py-4">
      <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{t("aiPage.title")}</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("aiPage.subtitle")}</p>

      <SourceChoice value={source} onChange={switchSource} />

      {source === "inapp" ? <InappPanel /> : <CustomPanel />}

      <SystemMessageSection />
    </div>
  );
}

function SourceChoice({ value, onChange }: { value: AISource; onChange: (next: AISource) => void }) {
  const { t } = useTranslation();
  const options: { key: AISource; title: string; body: string }[] = [
    { key: "inapp", title: t("aiPage.source.inapp"), body: t("aiPage.source.inappBody") },
    { key: "custom", title: t("aiPage.source.custom"), body: t("aiPage.source.customBody") },
  ];

  return (
    <div
      role="radiogroup"
      aria-label={t("aiPage.source.label")}
      className="mt-6 grid gap-1 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-1 sm:grid-cols-2"
    >
      {options.map((option) => {
        const on = value === option.key;
        return (
          <button
            key={option.key}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(option.key)}
            className={cn(
              "flex items-start gap-3 rounded-[var(--radius)] px-3 py-3 text-left transition-colors cursor-pointer",
              focusRing,
              on ? "bg-[var(--color-bg-hover)]" : "hover:bg-[var(--color-bg-hover)]/60",
            )}
          >
            <span
              aria-hidden
              className={cn(
                "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border",
                on ? "border-[var(--color-accent)]" : "border-[var(--color-text-muted)]",
              )}
            >
              {on && <span className="h-2 w-2 rounded-full bg-[var(--color-accent)]" />}
            </span>
            <span className="min-w-0">
              <span
                className={cn(
                  "block text-sm font-medium",
                  on ? "text-[var(--color-text-primary)]" : "text-[var(--color-text-secondary)]",
                )}
              >
                {option.title}
              </span>
              <span className="mt-0.5 block text-xs leading-relaxed text-[var(--color-text-muted)]">{option.body}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function Section({
  title,
  body,
  action,
  children,
}: {
  title: string;
  body?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-9">
      <div className="flex items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
          {body && <p className="mt-1 text-sm leading-relaxed text-[var(--color-text-secondary)]">{body}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      <div className="mt-3 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4 sm:p-5">
        {children}
      </div>
    </section>
  );
}

function Notice({ tone, children }: { tone: "warning" | "error"; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2.5 text-sm leading-relaxed text-[var(--color-text-secondary)]">
      <AlertTriangle
        aria-hidden
        className={cn(
          "mt-0.5 h-4 w-4 shrink-0",
          tone === "error" ? "text-[var(--color-error)]" : "text-[var(--color-warning)]",
        )}
      />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

// In-app

function InappPanel() {
  const { t } = useTranslation();
  const { activated, appInfo, busy, activate } = useAccountStore();
  const supported = inappSupported(appInfo);
  const [dialog, setDialog] = useState<"topup" | "export" | "restore" | null>(null);

  const handleActivate = async () => {
    try {
      await activate();
      toast.success(t("aiPage.inactive.activated"));
      // An unreachable catalogue is survivable: the picker below still offers it.
      await ensureDefaultModel().catch(() => undefined);
    } catch (err) {
      toast.error(t("aiPage.inactive.activateFailed", { reason: errorMessage(err) }));
    }
  };

  const dialogs = (
    <>
      {dialog === "topup" && <TopupDialog onClose={() => setDialog(null)} />}
      {dialog === "export" && <AccountKeyDialog mode="export" onClose={() => setDialog(null)} />}
      {dialog === "restore" && <AccountKeyDialog mode="restore" onClose={() => setDialog(null)} />}
    </>
  );

  if (!supported) {
    return (
      <Section title={t("aiPage.unsupported.title")}>
        <Notice tone="warning">
          <p>
            {appInfo?.latestVersion
              ? t("aiPage.unsupported.body", { version: appInfo.latestVersion })
              : t("aiPage.unsupported.bodyNoVersion")}
          </p>
          {appInfo?.downloadUrl && !IS_STORE_BUILD && (
            <Button className="mt-4 gap-2" onClick={() => openUrl(appInfo.downloadUrl)}>
              {t("aiPage.unsupported.download")}
              <ExternalLink aria-hidden className="h-4 w-4" />
            </Button>
          )}
        </Notice>
      </Section>
    );
  }

  if (!activated) {
    return (
      <>
        <Section title={t("aiPage.inactive.title")} body={t("aiPage.inactive.body")}>
          <Notice tone="warning">{t("aiPage.inactive.keyNote")}</Notice>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button onClick={() => void handleActivate()} disabled={busy} className="gap-2">
              {busy && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
              {t("aiPage.inactive.retry")}
            </Button>
            <Button variant="outline" onClick={() => setDialog("restore")}>
              {t("aiPage.inactive.restore")}
            </Button>
          </div>
          <p className="mt-4 border-t border-[var(--color-border)] pt-4 text-xs leading-relaxed text-[var(--color-text-muted)]">
            {t("aiPage.inactive.webNote")}
          </p>
        </Section>
        {dialogs}
      </>
    );
  }

  return (
    <>
      <BalanceSection onTopup={() => setDialog("topup")} />
      <InappModelSection />

      <Section title={t("aiPage.key.title")} body={t("aiPage.key.body")}>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setDialog("export")}>
            {t("aiPage.key.export")}
          </Button>
          <Button variant="outline" onClick={() => setDialog("restore")}>
            {t("aiPage.key.restore")}
          </Button>
        </div>
      </Section>

      <UsageSection />
      {dialogs}
    </>
  );
}

function BalanceSection({ onTopup }: { onTopup: () => void }) {
  const { t } = useTranslation();
  const { account, refreshing, error, refresh } = useAccountStore();

  const refreshButton = (
    <button
      type="button"
      onClick={() => void refresh()}
      disabled={refreshing}
      className={cn(
        "inline-flex min-h-9 items-center gap-1.5 rounded-full px-2.5 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer disabled:cursor-wait",
        focusRing,
      )}
    >
      <RefreshCw aria-hidden className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
      {refreshing ? t("aiPage.balance.refreshing") : t("aiPage.balance.refresh")}
    </button>
  );

  return (
    <Section title={t("aiPage.balance.title")} body={t("aiPage.balance.body")} action={refreshButton}>
      {account?.blocked && (
        <div className="mb-5">
          <Notice tone="error">{account.blockedReason ?? t("aiPage.balance.blocked")}</Notice>
        </div>
      )}

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          {account ? (
            <>
              <p className="text-4xl font-bold tabular-nums text-[var(--color-text-primary)]">
                {formatUsd(account.balanceUsd)}
              </p>
              {account.balanceIdr > 0 && (
                <p className="mt-1 text-sm tabular-nums text-[var(--color-text-secondary)]">
                  {t("aiPage.balance.approxIdr", { amount: formatIdr(account.balanceIdr) })}
                </p>
              )}
              <p className="mt-2 text-xs text-[var(--color-text-muted)]">
                {t("aiPage.balance.history", {
                  topped: formatUsd(account.toppedUpUsd),
                  spent: formatUsd(account.spentUsd),
                })}
              </p>
            </>
          ) : error ? (
            <p className="text-sm text-[var(--color-error)]">{t("aiPage.balance.loadFailed", { reason: error })}</p>
          ) : (
            <p className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
              {refreshing && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
              {t("aiPage.balance.unknown")}
            </p>
          )}
        </div>
        <Button onClick={onTopup} className="px-6">
          {t("aiPage.balance.topup")}
        </Button>
      </div>

      {account && (
        <>
          <TierLine membership={account.membership} />
          <AccountIdRow accountId={account.accountId} />
        </>
      )}
    </Section>
  );
}

function TierLine({ membership }: { membership: Membership }) {
  const { t } = useTranslation();
  const gold = membership.tier === "GOLD";
  const progress =
    membership.thresholdUsd > 0 ? Math.min(1, Math.max(0, membership.lifetimeTopupUsd / membership.thresholdUsd)) : 0;

  return (
    <div className="mt-5 border-t border-[var(--color-border)] pt-4">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="text-sm font-medium text-[var(--color-text-primary)]">
          {gold ? t("aiPage.tier.gold") : t("aiPage.tier.regular")}
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">
          {gold ? t("aiPage.tier.goldBody") : t("aiPage.tier.progress", { amount: formatUsd(membership.remainingUsd) })}
        </p>
      </div>
      {!gold && (
        <div
          role="progressbar"
          aria-label={t("aiPage.tier.progressLabel")}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress * 100)}
          className="mt-2.5 h-1 overflow-hidden rounded-full bg-[var(--color-bg-hover)]"
        >
          <div className="h-full rounded-full bg-[var(--color-text-secondary)]" style={{ width: `${progress * 100}%` }} />
        </div>
      )}
      {membership.groupUrl && (
        <button type="button" onClick={() => openUrl(membership.groupUrl!)} className={cn(textLink, "mt-1 text-xs")}>
          {t("aiPage.tier.joinGroup")}
          <ExternalLink aria-hidden className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function AccountIdRow({ accountId }: { accountId: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(accountId);
      setCopied(true);
      toast.success(t("aiPage.balance.copied"));
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("aiPage.balance.copyFailed"));
    }
  };

  return (
    <div className="mt-4 flex items-center justify-between gap-3 border-t border-[var(--color-border)] pt-3">
      <p className="min-w-0 text-xs text-[var(--color-text-muted)]">
        {t("aiPage.balance.accountId")}{" "}
        <span className="select-all break-all font-mono text-[var(--color-text-secondary)]">{accountId}</span>
      </p>
      <button
        type="button"
        onClick={() => void copy()}
        aria-label={t("aiPage.balance.copyId")}
        title={t("aiPage.balance.copyId")}
        className={cn(
          "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] cursor-pointer",
          focusRing,
        )}
      >
        {copied ? <Check aria-hidden className="h-4 w-4 text-[var(--color-success)]" /> : <Copy aria-hidden className="h-4 w-4" />}
      </button>
    </div>
  );
}

function InappModelSection() {
  const { t } = useTranslation();
  const model = useConfigStore((s) => s.config.ai.inapp.model);
  const setInappModel = useConfigStore((s) => s.setInappModel);
  const { models, modelsLoading, loadModels } = useAccountStore();
  // loadModels swallows its own failure, so "tried and still empty" is the only
  // way to tell a failed catalogue from one that has not been asked for yet.
  const [attempted, setAttempted] = useState(false);

  useEffect(() => {
    void loadModels().finally(() => setAttempted(true));
  }, [loadModels]);

  const available = useMemo(() => chatModels(models), [models]);
  const selected = available.find((m) => m.name === model);
  const loading = modelsLoading && !models;
  const failed = attempted && !modelsLoading && !models;

  const groups = useMemo<ComboboxGroup[]>(() => {
    const byProvider = new Map<string, ComboboxGroup>();
    for (const m of available) {
      const group = byProvider.get(m.provider) ?? { label: m.provider, options: [] };
      group.options.push({ value: m.name, label: m.name });
      byProvider.set(m.provider, group);
    }
    const list = [...byProvider.values()];
    if (model && !selected) list.unshift({ label: t("aiPage.model.saved"), options: [{ value: model, label: model }] });
    return list;
  }, [available, model, selected, t]);

  const perMillion = (perToken: number) => formatUsd(perToken * 1_000_000);
  const meta: string[] = [];
  if (selected) {
    meta.push(selected.provider);
    if (selected.inputCostPerToken !== null && selected.outputCostPerToken !== null) {
      meta.push(
        t("aiPage.model.price", {
          input: perMillion(selected.inputCostPerToken),
          output: perMillion(selected.outputCostPerToken),
        }),
      );
    } else if (selected.inputCostPerToken !== null) {
      meta.push(t("aiPage.model.priceInput", { input: perMillion(selected.inputCostPerToken) }));
    } else {
      meta.push(t("aiPage.model.priceUnknown"));
    }
    if (selected.maxInputTokens) meta.push(t("aiPage.model.context", { count: Math.round(selected.maxInputTokens / 1000) }));
  }

  return (
    <Section title={t("aiPage.model.title")} body={t("aiPage.model.body")}>
      <Combobox
        label={t("aiPage.model.label")}
        value={model}
        groups={groups}
        onChange={(next) =>
          setInappModel(next).catch((err) => toast.error(t("aiPage.saveFailed", { reason: errorMessage(err) })))
        }
        disabled={loading}
        placeholder={loading ? t("aiPage.model.loading") : t("aiPage.model.choose")}
        searchPlaceholder={t("aiPage.model.search")}
        emptyText={t("aiPage.model.empty")}
        triggerClassName={pickerTrigger}
      />
      {meta.length > 0 && <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-muted)]">{meta.join(" · ")}</p>}
      {failed && (
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--color-text-muted)]">
          <span>{t("aiPage.model.catalogFailed")}</span>
          <button type="button" onClick={() => void loadModels(true)} className={textLink}>
            {t("aiPage.model.retry")}
          </button>
        </div>
      )}
    </Section>
  );
}

type UsageState = { kind: "loading" } | { kind: "error" } | { kind: "ready"; rows: UsageLog[] };

function UsageSection() {
  const { t, i18n } = useTranslation();
  const [state, setState] = useState<UsageState>({ kind: "loading" });

  useEffect(() => {
    fetchUsage(jakartaDate(-6), jakartaDate(), 1, 10)
      .then((page) => setState({ kind: "ready", rows: page.data }))
      .catch((err) => {
        // An account that has never made a request is empty, not broken.
        if (errorCode(err) === "NOT_PROVISIONED") setState({ kind: "ready", rows: [] });
        else setState({ kind: "error" });
      });
  }, []);

  const when = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

  return (
    <Section title={t("aiPage.usage.title")} body={t("aiPage.usage.body")}>
      {state.kind === "loading" ? (
        <p className="flex items-center gap-2 py-4 text-sm text-[var(--color-text-muted)]">
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          {t("aiPage.usage.loading")}
        </p>
      ) : state.kind === "error" ? (
        <p className="py-4 text-sm text-[var(--color-text-muted)]">{t("aiPage.usage.failed")}</p>
      ) : state.rows.length === 0 ? (
        <div className="py-6 text-center">
          <p className="text-sm font-medium text-[var(--color-text-primary)]">{t("aiPage.usage.empty")}</p>
          <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-[var(--color-text-muted)]">
            {t("aiPage.usage.emptyBody")}
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-[var(--color-text-secondary)]">
            {t("aiPage.usage.summary", {
              count: state.rows.length,
              total: formatSpendUsd(state.rows.reduce((sum, row) => sum + row.spendUsd, 0)),
            })}
          </p>
          <div className="-mx-4 mt-3 overflow-x-auto sm:-mx-5">
            <table className="w-full min-w-[28rem] text-xs">
              <thead>
                <tr className="text-left text-[var(--color-text-muted)]">
                  <th scope="col" className="px-4 pb-2 font-medium sm:pl-5">{t("aiPage.usage.colModel")}</th>
                  <th scope="col" className="px-3 pb-2 text-right font-medium">{t("aiPage.usage.colTokens")}</th>
                  <th scope="col" className="px-3 pb-2 text-right font-medium">{t("aiPage.usage.colCost")}</th>
                  <th scope="col" className="px-4 pb-2 text-right font-medium sm:pr-5">{t("aiPage.usage.colTime")}</th>
                </tr>
              </thead>
              <tbody>
                {state.rows.map((row) => (
                  <tr key={row.requestId} className="border-t border-[var(--color-border)]">
                    <td className="max-w-[14rem] truncate px-4 py-2.5 text-[var(--color-text-primary)] sm:pl-5" title={row.model}>
                      {row.model}
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-[var(--color-text-secondary)]">
                      {row.totalTokens.toLocaleString(i18n.language)}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2.5 text-right tabular-nums",
                        row.status === "failure" ? "text-[var(--color-error)]" : "text-[var(--color-text-secondary)]",
                      )}
                    >
                      {row.status === "failure" ? t("aiPage.usage.failedRow") : formatSpendUsd(row.spendUsd)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-right text-[var(--color-text-muted)] sm:pr-5">
                      {when(row.startedAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Section>
  );
}

// Own API key

const PROVIDER_KEYS = ["ytclip", "apismart", "openai", "google", "groq", "custom"] as const;
type ProviderKey = (typeof PROVIDER_KEYS)[number];

function isProviderKey(key: string): key is ProviderKey {
  return (PROVIDER_KEYS as readonly string[]).includes(key);
}

function useProviderText() {
  const { t } = useTranslation();
  return (preset: AIProviderPreset) =>
    isProviderKey(preset.key)
      ? { name: t(`aiPage.providers.${preset.key}.name`), body: t(`aiPage.providers.${preset.key}.body`) }
      : { name: preset.name, body: preset.description };
}

function Field({
  id,
  label,
  help,
  children,
}: {
  id: string;
  label: string;
  help?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-[var(--color-text-primary)]">
        {label}
      </label>
      {children}
      {help && <p className="mt-1.5 text-xs leading-relaxed text-[var(--color-text-muted)]">{help}</p>}
    </div>
  );
}

function CustomPanel() {
  const { t } = useTranslation();
  const ids = useId();
  const providerText = useProviderText();
  const settings = useConfigStore((s) => s.config.ai.custom);
  const setCustomAI = useConfigStore((s) => s.setCustomAI);

  const initialPreset = presetForBaseUrl(settings.baseUrl);
  const [providerKey, setProviderKey] = useState(initialPreset.key);
  const [baseUrl, setBaseUrl] = useState(settings.baseUrl || initialPreset.baseUrl);
  const [apiKey, setApiKey] = useState(settings.apiKey || "");
  const [model, setModel] = useState(settings.model || "");
  const [models, setModels] = useState<string[]>(() =>
    settings.model && !FALLBACK_MODELS.includes(settings.model) ? [settings.model, ...FALLBACK_MODELS] : FALLBACK_MODELS,
  );
  const [loadingModels, setLoadingModels] = useState(false);
  const [saving, setSaving] = useState(false);

  const selectedPreset = useMemo(
    () => AI_PROVIDER_PRESETS.find((p) => p.key === providerKey) ?? AI_PROVIDER_PRESETS[0],
    [providerKey],
  );
  const isCustomEndpoint = providerKey === "custom";
  const signupUrl = selectedPreset.signupUrl;

  const providerGroups: ComboboxGroup[] = [
    { options: AI_PROVIDER_PRESETS.map((p) => ({ value: p.key, label: providerText(p).name })) },
  ];
  const modelGroups: ComboboxGroup[] = [
    {
      options: (model && !models.includes(model) ? [model, ...models] : models).map((m) => ({ value: m, label: m })),
    },
  ];

  const handleProviderChange = (value: string) => {
    const preset = AI_PROVIDER_PRESETS.find((p) => p.key === value) ?? AI_PROVIDER_PRESETS[0];
    setProviderKey(preset.key);
    setBaseUrl(preset.baseUrl);
  };

  const handleLoadModels = async () => {
    if (!apiKey.trim()) {
      toast.error(t("aiPage.custom.needKey"));
      return;
    }
    setLoadingModels(true);
    try {
      const loaded = await listAIModels(apiKey, baseUrl);
      setModels(loaded);
      if (loaded.length > 0 && !loaded.includes(model)) setModel(loaded[0]);
      toast.success(t("aiPage.custom.modelsLoaded", { count: loaded.length }));
    } catch (err) {
      console.error("Failed to load models", err);
      toast.error(t("aiPage.custom.modelsFailed", { reason: errorMessage(err) }));
      setModels((prev) => (prev.length ? prev : FALLBACK_MODELS));
    } finally {
      setLoadingModels(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey.trim()) {
      toast.error(t("aiPage.custom.needKey"));
      return;
    }
    if (!model.trim()) {
      toast.error(t("aiPage.custom.needModel"));
      return;
    }
    setSaving(true);
    try {
      const next: CustomAISettings = { baseUrl, apiKey, model };
      await setCustomAI(next);
      toast.success(t("aiPage.custom.saved"));
    } catch (err) {
      toast.error(t("aiPage.saveFailed", { reason: errorMessage(err) }));
    } finally {
      setSaving(false);
    }
  };

  const keyHint =
    selectedPreset.apiKeyFormat === "optional"
      ? t("aiPage.custom.apiKeyOptional")
      : selectedPreset.apiKeyFormat
        ? t("aiPage.custom.apiKeyFormat", { format: selectedPreset.apiKeyFormat })
        : null;

  return (
    <>
      <Section title={t("aiPage.custom.providerTitle")} body={t("aiPage.custom.providerBody")}>
        <Combobox
          label={t("aiPage.custom.providerLabel")}
          value={providerKey}
          groups={providerGroups}
          onChange={handleProviderChange}
          placeholder={t("aiPage.custom.providerLabel")}
          searchPlaceholder={t("aiPage.custom.searchProvider")}
          emptyText={t("aiPage.custom.noProvider")}
          triggerClassName={pickerTrigger}
        />
        <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-muted)]">{providerText(selectedPreset).body}</p>
        {signupUrl && (
          <p className="mt-2 flex flex-wrap items-center gap-x-1 text-xs text-[var(--color-text-secondary)]">
            {t("aiPage.custom.signup")}
            <button type="button" onClick={() => openUrl(signupUrl)} className={textLink}>
              {signupLabel(signupUrl)}
              <ExternalLink aria-hidden className="h-3 w-3" />
            </button>
          </p>
        )}
      </Section>

      <Section title={t("aiPage.custom.connectionTitle")}>
        <div className="space-y-5">
          {isCustomEndpoint ? (
            <Field id={`${ids}-url`} label={t("aiPage.custom.baseUrl")} help={t("aiPage.custom.baseUrlHelp")}>
              <Input
                id={`${ids}-url`}
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                spellCheck={false}
                className="h-11 font-mono"
              />
            </Field>
          ) : (
            <Field id={`${ids}-url`} label={t("aiPage.custom.baseUrl")} help={t("aiPage.custom.baseUrlFixed")}>
              <Input id={`${ids}-url`} value={baseUrl} readOnly className="h-11 font-mono text-[var(--color-text-muted)]" />
            </Field>
          )}

          <Field
            id={`${ids}-key`}
            label={t("aiPage.custom.apiKey")}
            help={keyHint ? `${keyHint}. ${t("aiPage.custom.apiKeyHelp")}` : t("aiPage.custom.apiKeyHelp")}
          >
            <Input
              id={`${ids}-key`}
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={t("aiPage.custom.apiKeyPlaceholder")}
              autoComplete="off"
              spellCheck={false}
              className="h-11"
            />
          </Field>

          <Field id={`${ids}-model`} label={t("aiPage.custom.model")} help={t("aiPage.custom.modelHelp")}>
            <div className="flex gap-2">
              <div className="min-w-0 flex-1">
                <Combobox
                  label={t("aiPage.custom.modelPick")}
                  value={model}
                  groups={modelGroups}
                  onChange={setModel}
                  placeholder={t("aiPage.custom.modelChoose")}
                  searchPlaceholder={t("aiPage.custom.modelSearch")}
                  emptyText={t("aiPage.custom.modelEmpty")}
                  triggerClassName={pickerTrigger}
                />
              </div>
              <Button
                variant="outline"
                onClick={() => void handleLoadModels()}
                disabled={loadingModels}
                className="h-11 shrink-0 gap-2"
              >
                {loadingModels && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
                {loadingModels ? t("aiPage.custom.loadingModels") : t("aiPage.custom.loadModels")}
              </Button>
            </div>
            <Input
              id={`${ids}-model`}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              aria-label={t("aiPage.custom.modelManual")}
              placeholder={t("aiPage.custom.modelManualPlaceholder")}
              spellCheck={false}
              className="mt-2 h-11 font-mono"
            />
          </Field>
        </div>

        <div className="mt-6 flex justify-end border-t border-[var(--color-border)] pt-4">
          <Button onClick={() => void handleSave()} disabled={saving} className="gap-2 px-6">
            {saving && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
            {saving ? t("aiPage.custom.saving") : t("aiPage.custom.save")}
          </Button>
        </div>
      </Section>
    </>
  );
}

/**
 * Shared by both sources: it is a prompt, not a credential, so switching
 * provider should not cost the user the instructions they tuned.
 */
function SystemMessageSection() {
  const { t } = useTranslation();
  const id = useId();
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
      toast.success(t("aiPage.system.saved"));
    } catch (err) {
      toast.error(t("aiPage.saveFailed", { reason: errorMessage(err) }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section title={t("aiPage.system.title")} body={t("aiPage.system.body")}>
      <textarea
        id={id}
        aria-label={t("aiPage.system.label")}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={t("aiPage.system.placeholder")}
        className={cn(
          "min-h-[180px] w-full resize-y rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] px-3 py-2.5 text-sm leading-relaxed text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]",
          focusRing,
        )}
      />
      <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-muted)]">{t("aiPage.system.help")}</p>
      {dirty && (
        <div className="mt-4 flex justify-end">
          <Button variant="outline" onClick={() => void save()} disabled={saving} className="gap-2">
            {saving && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
            {t("aiPage.system.save")}
          </Button>
        </div>
      )}
    </Section>
  );
}
