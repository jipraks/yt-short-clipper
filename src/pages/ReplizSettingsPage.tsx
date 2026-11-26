import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ExternalLink, Loader2 } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { useConfigStore } from "@/stores/configStore";
import { replizListAccounts, type ReplizAccount } from "@/hooks/repliz";
import replizMark from "@/assets/brands/repliz-mark.png";

const SIGNUP_URL = "https://s.id/ytrepliz";
const DASHBOARD_URL = "https://repliz.com";

const PLATFORM_NAMES: Record<string, string> = {
  youtube: "YouTube",
  tiktok: "TikTok",
  instagram: "Instagram",
  facebook: "Facebook",
  threads: "Threads",
};

/** State of the keys that are saved, not of what is typed in the form. */
type Status =
  | { kind: "none" }
  | { kind: "checking" }
  | { kind: "connected"; accounts: ReplizAccount[] }
  | { kind: "rejected"; reason: string };

/** Sidecar errors carry a stderr dump; the first part is the sentence to show. */
function shortReason(err: unknown): string {
  return String(err).split("\n\nstderr:")[0].replace(/^Sidecar error: /, "").trim();
}

/**
 * Repliz connection: what it adds, whether the saved keys work and which
 * social accounts they reach, the key form, and a way out. Connecting checks
 * the keys with Repliz first and saves them only when Repliz accepts them.
 */
export function ReplizSettingsPage() {
  const { t } = useTranslation();
  const { config, loaded, load, setRepliz } = useConfigStore();
  const saved = config.repliz;
  const hasSaved = saved.accessKey.trim() !== "" && saved.secretKey.trim() !== "";

  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [status, setStatus] = useState<Status>({ kind: "none" });
  const [connecting, setConnecting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const checkedFor = useRef("");

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!loaded) return;
    setAccessKey(saved.accessKey);
    setSecretKey(saved.secretKey);
  }, [loaded, saved.accessKey, saved.secretKey]);

  const checkSaved = useCallback(async () => {
    setStatus({ kind: "checking" });
    try {
      setStatus({ kind: "connected", accounts: await replizListAccounts(saved.accessKey, saved.secretKey) });
    } catch (err) {
      setStatus({ kind: "rejected", reason: shortReason(err) });
    }
  }, [saved.accessKey, saved.secretKey]);

  // Check the saved keys once on open, and again whenever they change.
  useEffect(() => {
    if (!loaded) return;
    if (!hasSaved) {
      checkedFor.current = "";
      setStatus({ kind: "none" });
      return;
    }
    const key = `${saved.accessKey}:${saved.secretKey}`;
    if (checkedFor.current === key) return;
    checkedFor.current = key;
    void checkSaved();
  }, [loaded, hasSaved, saved.accessKey, saved.secretKey, checkSaved]);

  const connect = async () => {
    const a = accessKey.trim();
    const s = secretKey.trim();
    if (!a || !s) {
      setFormError(t("onboardingRepliz.connect.missing"));
      return;
    }
    setFormError(null);
    setConnecting(true);
    let accounts: ReplizAccount[];
    try {
      accounts = await replizListAccounts(a, s);
    } catch (err) {
      setFormError(t("onboardingRepliz.connect.failed", { reason: shortReason(err) }));
      setConnecting(false);
      return;
    }
    try {
      await setRepliz({ accessKey: a, secretKey: s });
      checkedFor.current = `${a}:${s}`;
      setStatus({ kind: "connected", accounts });
      toast.success(t("replizSettings.connected"));
    } catch {
      setFormError(t("onboardingRepliz.connect.saveFailed"));
    } finally {
      setConnecting(false);
    }
  };

  const disconnect = async (close: () => void) => {
    setDisconnecting(true);
    try {
      await setRepliz({ accessKey: "", secretKey: "" });
      setAccessKey("");
      setSecretKey("");
      setFormError(null);
      toast.success(t("replizSettings.disconnect.done"));
      close();
    } catch {
      toast.error(t("replizSettings.disconnect.failed"));
    } finally {
      setDisconnecting(false);
    }
  };

  const ready = status.kind === "connected" ? status.accounts.filter((a) => a.is_connected) : [];

  return (
    <div className="mx-auto max-w-2xl py-4">
      <div className="flex items-center gap-3">
        <img src={replizMark} alt="" aria-hidden className="h-8 w-auto shrink-0" />
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{t("replizSettings.title")}</h1>
      </div>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("replizSettings.subtitle")}</p>

      {/* Connection status */}
      <section
        aria-live="polite"
        className="mt-8 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-5"
      >
        {!loaded ? (
          <p className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
            {t("replizSettings.status.loading")}
          </p>
        ) : status.kind === "checking" ? (
          <p className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
            {t("replizSettings.status.checking")}
          </p>
        ) : status.kind === "rejected" ? (
          <>
            <p className="text-sm font-medium text-[var(--color-error)] leading-relaxed">
              {t("replizSettings.status.rejected", { reason: status.reason })}
            </p>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("replizSettings.status.rejectedHint")}</p>
          </>
        ) : status.kind === "connected" ? (
          ready.length === 0 ? (
            <p className="text-sm text-[var(--color-warning)] leading-relaxed">{t("onboardingRepliz.connect.noAccounts")}</p>
          ) : (
            <>
              <p className="text-sm font-medium text-[var(--color-success)]">
                {t("replizSettings.status.connected", { count: ready.length })}
              </p>
              <ul className="mt-3 divide-y divide-[var(--color-border)] border-t border-[var(--color-border)]">
                {status.accounts.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                    <span className="min-w-0 truncate text-[var(--color-text-primary)]">
                      {a.name || a.username}
                      {a.username && a.name && (
                        <span className="ml-1.5 text-[var(--color-text-muted)]">@{a.username}</span>
                      )}
                    </span>
                    <span className="shrink-0 text-xs text-[var(--color-text-muted)]">
                      {PLATFORM_NAMES[a.type] ?? a.type}
                      {!a.is_connected && <> · {t("replizSettings.status.accountOff")}</>}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )
        ) : (
          <p className="text-sm text-[var(--color-text-secondary)]">{t("replizSettings.status.notConnected")}</p>
        )}

        {loaded && (
          <button
            type="button"
            onClick={() => openUrl(DASHBOARD_URL).catch(console.error)}
            className="mt-3 inline-flex min-h-9 items-center gap-1.5 rounded-full text-sm font-medium text-[var(--color-accent)] hover:underline cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            {t("replizSettings.dashboard")}
            <ExternalLink aria-hidden className="h-3.5 w-3.5" />
          </button>
        )}
      </section>

      {/* What Repliz adds, for anyone who has not connected yet */}
      {loaded && !hasSaved && (
        <section className="mt-9">
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{t("replizSettings.pitch.title")}</h2>
          <ul className="mt-3 space-y-2">
            {(["many", "schedule", "setup"] as const).map((key) => (
              <li key={key} className="flex gap-3 text-sm text-[var(--color-text-primary)] leading-relaxed">
                <span aria-hidden className="mt-[0.55em] h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-accent)]" />
                {t(`onboardingRepliz.benefits.${key}`)}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("onboardingRepliz.plan.why")}</p>
          <Button variant="outline" onClick={() => openUrl(SIGNUP_URL).catch(console.error)} className="mt-4 h-11 gap-2 px-4">
            {t("onboardingRepliz.plan.signup")}
            <ExternalLink aria-hidden className="h-4 w-4" />
          </Button>
        </section>
      )}

      {/* Keys */}
      <section className="mt-9">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{t("replizSettings.keys.title")}</h2>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("onboardingRepliz.connect.body")}</p>

        <form
          className="mt-4 space-y-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-5"
          onSubmit={(e) => {
            e.preventDefault();
            void connect();
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
              disabled={!loaded}
              onChange={(e) => {
                setAccessKey(e.target.value);
                setFormError(null);
              }}
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
                disabled={!loaded}
                onChange={(e) => {
                  setSecretKey(e.target.value);
                  setFormError(null);
                }}
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
            <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">{t("replizSettings.keys.stored")}</p>
          </div>

          {formError && (
            <p role="alert" className="text-sm text-[var(--color-error)] leading-relaxed">
              {formError}
            </p>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <Button type="submit" disabled={connecting || !loaded} className="h-11 gap-2 px-5">
              {connecting && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
              {connecting ? t("onboardingRepliz.connect.checking") : t("onboardingRepliz.connect.action")}
            </Button>
            {hasSaved && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => setConfirmDisconnect(true)}
                disabled={connecting}
                className="h-11 px-4 text-[var(--color-text-secondary)]"
              >
                {t("replizSettings.disconnect.action")}
              </Button>
            )}
          </div>
        </form>
      </section>

      {confirmDisconnect && (
        <Modal
          title={t("replizSettings.disconnect.title")}
          closeLabel={t("replizSettings.disconnect.close")}
          onClose={() => setConfirmDisconnect(false)}
        >
          {(close) => (
            <>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {t("replizSettings.disconnect.body")}
              </p>
              <div className="mt-6 flex justify-end gap-2">
                <Button variant="ghost" onClick={close} disabled={disconnecting} className="h-11 px-4">
                  {t("replizSettings.disconnect.cancel")}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => void disconnect(close)}
                  disabled={disconnecting}
                  className="h-11 gap-2 px-4 text-[var(--color-error)]"
                >
                  {disconnecting && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
                  {disconnecting ? t("replizSettings.disconnect.working") : t("replizSettings.disconnect.confirm")}
                </Button>
              </div>
            </>
          )}
        </Modal>
      )}
    </div>
  );
}
