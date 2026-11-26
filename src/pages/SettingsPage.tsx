import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronRight, Loader2, Minus, Plus, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { detectGpu, MAX_CLIP_PADDING, type ClipPaddingSettings, type GpuDetection } from "@/hooks/appConfig";
import { useConfigStore } from "@/stores/configStore";
import { APP_VERSION } from "@/config/version";
import { cn } from "@/lib/utils";

const LANGUAGES = ["id", "en"] as const;

/**
 * Everything adjustable, grouped by what it changes: the app, the clips,
 * their timing, rendering speed, posting. Rows that lead to another page are
 * whole-row links with their current state on the right.
 */
export function SettingsPage() {
  const { t } = useTranslation();
  const { config, loaded, changeLanguage, setGpuAcceleration, setClipPadding } = useConfigStore();
  const [detection, setDetection] = useState<GpuDetection | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [savingGpu, setSavingGpu] = useState(false);
  const [savingLanguage, setSavingLanguage] = useState(false);

  const runDetect = async () => {
    setDetecting(true);
    try {
      setDetection(await detectGpu());
    } catch (err) {
      console.error("GPU detection failed", err);
      toast.error(t("settingsPage.gpu.detectFailed"));
    } finally {
      setDetecting(false);
    }
  };

  useEffect(() => {
    void runDetect();
    // Once, on open.
  }, []);

  const encoderAvailable = detection?.encoder.available ?? false;
  const gpuOn = config.gpuAcceleration.enabled && encoderAvailable;

  const toggleGpu = async (next: boolean) => {
    setSavingGpu(true);
    try {
      await setGpuAcceleration(next);
      toast.success(next ? t("settingsPage.gpu.enabled") : t("settingsPage.gpu.disabled"));
    } catch {
      toast.error(t("settingsPage.saveFailed"));
    } finally {
      setSavingGpu(false);
    }
  };

  const pickLanguage = async (language: (typeof LANGUAGES)[number]) => {
    if (language === config.language || savingLanguage) return;
    setSavingLanguage(true);
    try {
      await changeLanguage(language);
    } catch {
      toast.error(t("settingsPage.saveFailed"));
    } finally {
      setSavingLanguage(false);
    }
  };

  const savePadding = async (next: ClipPaddingSettings) => {
    try {
      await setClipPadding(next);
    } catch {
      toast.error(t("settingsPage.saveFailed"));
    }
  };

  const creditText = config.creditWatermark.text.trim();
  const hasLogo = config.watermark.imagePath.trim() !== "";
  const replizOn = config.repliz.accessKey.trim() !== "" && config.repliz.secretKey.trim() !== "";
  const totalPadding = config.clipPadding.leadIn + config.clipPadding.tailOut;

  const gpuStatus = detecting
    ? t("settingsPage.gpu.detecting")
    : !detection
      ? t("settingsPage.gpu.notChecked")
      : detection.gpu.available && encoderAvailable
        ? t("settingsPage.gpu.detected", { name: detection.gpu.name })
        : t("settingsPage.gpu.none");

  return (
    <div className="mx-auto max-w-2xl py-4">
      <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{t("settingsPage.title")}</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("settingsPage.subtitle")}</p>

      <Section title={t("settingsPage.general.title")}>
        <Row title={t("settingsPage.general.language")} body={t("settingsPage.general.languageBody")}>
          <div
            role="radiogroup"
            aria-label={t("settingsPage.general.language")}
            className="inline-flex rounded-full border border-[var(--color-border)] p-0.5"
          >
            {LANGUAGES.map((code) => {
              const on = config.language === code;
              return (
                <button
                  key={code}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  disabled={!loaded || savingLanguage}
                  onClick={() => void pickLanguage(code)}
                  className={cn(
                    "rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors cursor-pointer disabled:cursor-wait focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]",
                    on
                      ? "bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
                  )}
                >
                  {t(`common.language.${code}`)}
                </button>
              );
            })}
          </div>
        </Row>
      </Section>

      <Section title={t("settingsPage.clipLook.title")} body={t("settingsPage.clipLook.body")}>
        <LinkRow
          to="/settings/watermark"
          title={t("settingsPage.clipLook.logo")}
          body={hasLogo ? t("settingsPage.clipLook.logoSet") : t("settingsPage.clipLook.logoUnset")}
          status={hasLogo ? t("settingsPage.set") : t("settingsPage.notSet")}
          on={hasLogo}
        />
        <LinkRow
          to="/settings/credit"
          title={t("settingsPage.clipLook.credit")}
          body={creditText ? t("settingsPage.clipLook.creditSet", { text: creditText }) : t("settingsPage.clipLook.creditUnset")}
          status={creditText ? t("settingsPage.set") : t("settingsPage.notSet")}
          on={!!creditText}
        />
        <LinkRow to="/settings/hook-style" title={t("settingsPage.clipLook.hook")} body={t("settingsPage.clipLook.hookBody")} />
      </Section>

      <Section title={t("settingsPage.timing.title")} body={t("settingsPage.timing.body")}>
        <Row title={t("settingsPage.timing.leadIn")} body={t("settingsPage.timing.leadInBody")}>
          <SecondsStepper
            field={t("settingsPage.timing.leadIn")}
            value={config.clipPadding.leadIn}
            disabled={!loaded}
            onCommit={(leadIn) => void savePadding({ ...config.clipPadding, leadIn })}
          />
        </Row>
        <Row title={t("settingsPage.timing.tailOut")} body={t("settingsPage.timing.tailOutBody")}>
          <SecondsStepper
            field={t("settingsPage.timing.tailOut")}
            value={config.clipPadding.tailOut}
            disabled={!loaded}
            onCommit={(tailOut) => void savePadding({ ...config.clipPadding, tailOut })}
          />
        </Row>
        <p className="border-t border-[var(--color-border)] py-3.5 text-xs text-[var(--color-text-muted)] leading-relaxed">
          {totalPadding === 0
            ? t("settingsPage.timing.none")
            : t("settingsPage.timing.total", { seconds: Number(totalPadding.toFixed(1)).toLocaleString() })}
        </p>
      </Section>

      <Section title={t("settingsPage.gpu.title")}>
        <Row title={t("settingsPage.gpu.toggle")} body={t("settingsPage.gpu.toggleBody")}>
          <div className="flex items-center gap-2">
            {savingGpu && <Loader2 aria-hidden className="h-4 w-4 animate-spin text-[var(--color-text-muted)]" />}
            <Switch
              checked={gpuOn}
              onCheckedChange={(v) => void toggleGpu(v)}
              disabled={!encoderAvailable || detecting || savingGpu || !loaded}
            />
          </div>
        </Row>
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-t border-[var(--color-border)] py-3.5 text-xs">
          <div className="min-w-0 space-y-0.5 text-[var(--color-text-muted)]">
            <p>{gpuStatus}</p>
            <p>
              {t("settingsPage.gpu.using", {
                encoder: gpuOn ? detection?.encoder.name : t("settingsPage.gpu.cpu"),
              })}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void runDetect()}
            disabled={detecting}
            className="inline-flex min-h-9 items-center gap-1.5 rounded-full px-2 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer disabled:cursor-wait focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            <RefreshCw aria-hidden className={cn("h-3.5 w-3.5", detecting && "animate-spin")} />
            {t("settingsPage.gpu.redetect")}
          </button>
        </div>
      </Section>

      <Section title={t("settingsPage.integrations.title")}>
        <LinkRow
          to="/repliz"
          title={t("settingsPage.integrations.repliz")}
          body={replizOn ? t("settingsPage.integrations.replizOn") : t("settingsPage.integrations.replizOff")}
          status={replizOn ? t("settingsPage.connected") : t("settingsPage.notSet")}
          on={replizOn}
        />
      </Section>

      <Section title={t("settingsPage.about.title")}>
        <LinkRow to="/settings/credits" title={t("settingsPage.about.credits")} body={t("settingsPage.about.creditsBody")} />
        <p className="border-t border-[var(--color-border)] py-3.5 text-xs text-[var(--color-text-muted)]">
          {t("settingsPage.about.version", { version: APP_VERSION })}
        </p>
      </Section>
    </div>
  );
}

function Section({ title, body, children }: { title: string; body?: string; children: React.ReactNode }) {
  return (
    <section className="mt-9">
      <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
      {body && <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{body}</p>}
      <div className="mt-3 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] px-4 [&>*:first-child]:border-t-0">
        {children}
      </div>
    </section>
  );
}

function Row({ title, body, children }: { title: string; body?: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-t border-[var(--color-border)] py-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-[var(--color-text-primary)]">{title}</p>
        {body && <p className="mt-0.5 text-xs text-[var(--color-text-muted)] leading-relaxed">{body}</p>}
      </div>
      {children && <div className="shrink-0">{children}</div>}
    </div>
  );
}

/** A row that opens another settings page, with that setting's state on the right. */
function LinkRow({ to, title, body, status, on }: { to: string; title: string; body: string; status?: string; on?: boolean }) {
  return (
    <Link
      to={to}
      className="group -mx-4 flex items-center justify-between gap-4 border-t border-[var(--color-border)] px-4 py-4 transition-colors hover:bg-[var(--color-bg-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--color-border-focus)] first:rounded-t-[var(--radius-lg)] last:rounded-b-[var(--radius-lg)]"
    >
      <span className="min-w-0">
        <span className="block text-sm font-medium text-[var(--color-text-primary)]">{title}</span>
        <span className="mt-0.5 block truncate text-xs text-[var(--color-text-muted)]">{body}</span>
      </span>
      <span className="flex shrink-0 items-center gap-2">
        {status && (
          <span className={cn("text-xs", on ? "text-[var(--color-success)]" : "text-[var(--color-text-muted)]")}>{status}</span>
        )}
        <ChevronRight aria-hidden className="h-4 w-4 text-[var(--color-text-muted)] transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

/**
 * Seconds, in half-second steps with − and +, or typed. Typing commits on
 * blur or Enter, so a half-typed "1." is never saved; anything unparseable
 * snaps back to the stored value.
 */
function SecondsStepper({
  field,
  value,
  disabled,
  onCommit,
}: {
  field: string;
  value: number;
  disabled: boolean;
  onCommit: (seconds: number) => void;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  const apply = (next: number) => {
    const clamped = Math.min(Math.max(0, Math.round(next * 10) / 10), MAX_CLIP_PADDING);
    setDraft(String(clamped));
    if (clamped !== value) onCommit(clamped);
  };

  const commitDraft = () => {
    const parsed = Number(draft.replace(",", "."));
    if (!Number.isFinite(parsed) || parsed < 0) {
      setDraft(String(value));
      return;
    }
    apply(parsed);
  };

  const step = "inline-flex h-9 w-9 items-center justify-center rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]";

  return (
    <div className="flex items-center gap-1 rounded-full border border-[var(--color-border)] p-0.5">
      <button
        type="button"
        onClick={() => apply(value - 0.5)}
        disabled={disabled || value <= 0}
        aria-label={t("settingsPage.timing.decrease", { field })}
        className={step}
      >
        <Minus aria-hidden className="h-4 w-4" />
      </button>
      <label className="flex items-baseline gap-0.5">
        <input
          type="text"
          inputMode="decimal"
          value={draft}
          disabled={disabled}
          aria-label={field}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitDraft}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
          }}
          className="w-9 bg-transparent text-right text-sm font-semibold tabular-nums text-[var(--color-text-primary)] outline-none"
        />
        <span className="text-xs text-[var(--color-text-muted)]">{t("settingsPage.timing.unit")}</span>
      </label>
      <button
        type="button"
        onClick={() => apply(value + 0.5)}
        disabled={disabled || value >= MAX_CLIP_PADDING}
        aria-label={t("settingsPage.timing.increase", { field })}
        className={step}
      >
        <Plus aria-hidden className="h-4 w-4" />
      </button>
    </div>
  );
}
