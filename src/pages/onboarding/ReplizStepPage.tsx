import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { replizListAccounts, type ReplizAccount } from "@/hooks/repliz";
import { useConfigStore } from "@/stores/configStore";
import { formatIdr } from "@/utils/format";
import replizMark from "@/assets/brands/repliz-mark.png";

const SIGNUP_URL = "https://s.id/ytrepliz";

/**
 * Repliz Premium prices in rupiah, copied from Repliz's pricing page on
 * 26 November 2026 (the copy says so on screen). `full` is what the same
 * months cost billed monthly.
 */
const PREMIUM_PRICES = [
  { months: 1, price: 29_000 },
  { months: 3, price: 79_000, perMonth: 26_333, full: 87_000, saving: 9 },
  { months: 6, price: 139_000, perMonth: 23_167, full: 174_000, saving: 20 },
  { months: 12, price: 249_000, perMonth: 20_750, full: 348_000, saving: 28 },
] as const;

const FEATURES = ["accounts", "scheduled", "inbox", "ai", "research"] as const;

type Connect =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "connected"; accounts: ReplizAccount[] }
  | { kind: "error"; message: string };

/** Sidecar errors carry a stderr dump; the first part is the sentence to show. */
function shortReason(err: unknown): string {
  return String(err).split("\n\nstderr:")[0].replace(/^Sidecar error: /, "").trim();
}

/**
 * First-launch setup, step: Repliz. Explains what it adds to Cuplik and what
 * Premium costs, then connects the account. It can be skipped with a small
 * link; the main button waits for a working connection.
 */
export function ReplizStepPage({ onReadyChange }: { onReadyChange: (ready: boolean) => void }) {
  const { t } = useTranslation();
  const saved = useConfigStore((s) => s.config.repliz);
  const setRepliz = useConfigStore((s) => s.setRepliz);
  const alreadyConnected = saved.accessKey.trim() !== "" && saved.secretKey.trim() !== "";

  const [months, setMonths] = useState<number>(1);
  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [connect, setConnect] = useState<Connect>({ kind: "idle" });

  const plan = PREMIUM_PRICES.find((p) => p.months === months) ?? PREMIUM_PRICES[0];
  const ready = connect.kind === "connected" || (connect.kind === "idle" && alreadyConnected);
  useEffect(() => onReadyChange(ready), [ready, onReadyChange]);

  const check = async () => {
    const a = accessKey.trim();
    const s = secretKey.trim();
    if (!a || !s) {
      setConnect({ kind: "error", message: t("onboardingRepliz.connect.missing") });
      return;
    }
    setConnect({ kind: "checking" });
    let accounts: ReplizAccount[];
    try {
      accounts = await replizListAccounts(a, s);
    } catch (err) {
      setConnect({ kind: "error", message: t("onboardingRepliz.connect.failed", { reason: shortReason(err) }) });
      return;
    }
    try {
      await setRepliz({ accessKey: a, secretKey: s });
      setConnect({ kind: "connected", accounts });
    } catch {
      setConnect({ kind: "error", message: t("onboardingRepliz.connect.saveFailed") });
    }
  };

  return (
    <>
      <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{t("onboardingRepliz.title")}</h1>
      <p className="mt-2 text-base text-[var(--color-text-secondary)] leading-relaxed">
        {t("onboardingRepliz.lead")}
      </p>
      <ul className="mt-4 space-y-2">
        {(["many", "schedule", "setup"] as const).map((key) => (
          <li key={key} className="flex gap-3 text-sm text-[var(--color-text-primary)] leading-relaxed">
            <span aria-hidden className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-accent)]" />
            {t(`onboardingRepliz.benefits.${key}`)}
          </li>
        ))}
      </ul>

      {/* Premium, the plan Cuplik needs */}
      <section className="mt-8 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-card)] p-5">
        <div className="flex items-center gap-3">
          <img src={replizMark} alt="" aria-hidden className="h-7 w-auto shrink-0" />
          <h2 className="text-lg font-bold text-[var(--color-text-primary)]">{t("onboardingRepliz.plan.name")}</h2>
        </div>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("onboardingRepliz.plan.why")}</p>

        <fieldset className="mt-4">
          <legend className="sr-only">{t("onboardingRepliz.plan.durationLabel")}</legend>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 rounded-[var(--radius-sm)] bg-[var(--color-bg-primary)] p-1">
            {PREMIUM_PRICES.map((p) => {
              const active = p.months === months;
              return (
                <label
                  key={p.months}
                  className={`flex min-h-11 items-center justify-center rounded-[calc(var(--radius-sm)-2px)] px-2 text-sm font-medium cursor-pointer transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[var(--color-border-focus)] ${
                    active
                      ? "bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
                      : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  <input
                    type="radio"
                    name="repliz-months"
                    value={p.months}
                    checked={active}
                    onChange={() => setMonths(p.months)}
                    className="sr-only"
                  />
                  {t("onboardingRepliz.plan.months", { count: p.months })}
                </label>
              );
            })}
          </div>
        </fieldset>

        <div className="mt-4" aria-live="polite">
          <p className="text-3xl font-bold tabular-nums text-[var(--color-text-primary)]">{formatIdr(plan.price)}</p>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            {t("onboardingRepliz.plan.months", { count: plan.months })}
            {"perMonth" in plan && <> · {t("onboardingRepliz.plan.perMonth", { price: formatIdr(plan.perMonth) })}</>}
          </p>
          {"saving" in plan && (
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              <s className="text-[var(--color-text-muted)]">{formatIdr(plan.full)}</s>{" "}
              <span className="text-[var(--color-success)]">{t("onboardingRepliz.plan.saving", { percent: plan.saving })}</span>
            </p>
          )}
        </div>

        <ul className="mt-5 space-y-2">
          {FEATURES.map((key) => (
            <li key={key} className="flex gap-3 text-sm text-[var(--color-text-secondary)] leading-relaxed">
              <span aria-hidden className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-text-muted)]" />
              {t(`onboardingRepliz.plan.features.${key}`)}
            </li>
          ))}
        </ul>

        <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-2">
          <Button variant="outline" onClick={() => openUrl(SIGNUP_URL).catch(console.error)} className="h-11 px-4">
            {t("onboardingRepliz.plan.signup")}
          </Button>
          <p className="text-xs text-[var(--color-text-muted)]">{t("onboardingRepliz.plan.priceNote")}</p>
        </div>
      </section>

      {/* Connect */}
      <section className="mt-8">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{t("onboardingRepliz.connect.title")}</h2>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("onboardingRepliz.connect.body")}</p>

        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            void check();
          }}
        >
          <div className="space-y-1.5">
            <label htmlFor="repliz-access" className="text-sm font-medium text-[var(--color-text-secondary)]">
              {t("onboardingRepliz.connect.accessKey")}
            </label>
            <Input
              id="repliz-access"
              value={accessKey}
              autoComplete="off"
              spellCheck={false}
              onChange={(e) => setAccessKey(e.target.value)}
              className="h-11 font-mono text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="repliz-secret" className="text-sm font-medium text-[var(--color-text-secondary)]">
              {t("onboardingRepliz.connect.secretKey")}
            </label>
            <div className="flex gap-2">
              <Input
                id="repliz-secret"
                type={showSecret ? "text" : "password"}
                value={secretKey}
                autoComplete="off"
                spellCheck={false}
                onChange={(e) => setSecretKey(e.target.value)}
                className="h-11 flex-1 font-mono text-sm"
              />
              <Button
                type="button"
                variant="outline"
                aria-pressed={showSecret}
                onClick={() => setShowSecret((v) => !v)}
                className="h-11 px-4"
              >
                {showSecret ? t("onboardingRepliz.connect.hide") : t("onboardingRepliz.connect.show")}
              </Button>
            </div>
          </div>
          <Button
            type="submit"
            variant="outline"
            disabled={connect.kind === "checking"}
            className="h-11 px-5"
          >
            {connect.kind === "checking" ? t("onboardingRepliz.connect.checking") : t("onboardingRepliz.connect.action")}
          </Button>
        </form>

        <div aria-live="polite" className="mt-3">
          {connect.kind === "idle" && alreadyConnected && (
            <p className="text-sm text-[var(--color-success)]">{t("onboardingRepliz.connect.alreadyConnected")}</p>
          )}
          {connect.kind === "connected" &&
            (connect.accounts.length === 0 ? (
              <p className="text-sm text-[var(--color-warning)] leading-relaxed">{t("onboardingRepliz.connect.noAccounts")}</p>
            ) : (
              <div className="text-sm">
                <p className="text-[var(--color-success)]">
                  {t("onboardingRepliz.connect.connected", { count: connect.accounts.length })}
                </p>
                <ul className="mt-2 space-y-1 text-[var(--color-text-secondary)]">
                  {connect.accounts.map((a) => (
                    <li key={a.id}>
                      {a.name || a.username} <span className="text-[var(--color-text-muted)]">({a.type})</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
        {connect.kind === "error" && (
          <p role="alert" className="mt-3 text-sm text-[var(--color-error)] leading-relaxed">
            {connect.message}
          </p>
        )}
      </section>

    </>
  );
}
