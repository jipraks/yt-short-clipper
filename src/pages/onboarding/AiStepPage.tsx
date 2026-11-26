import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { AccountKeyDialog } from "@/components/AccountKeyDialog";
import { TopupDialog } from "@/components/TopupDialog";
import { useAccountStore, ensureDefaultModel, inappSupported } from "@/stores/accountStore";
import { useConfigStore } from "@/stores/configStore";
import { formatIdr, formatUsd } from "@/utils/format";
import { Step } from "./Step";

type Dialog = null | "backup" | "restore" | "topup";

/**
 * First-launch setup, step: the in-app AI balance. The account itself is
 * provisioned on launch by the account store; this step shows where it
 * stands, gets the Account Key saved, and offers a first top-up, which can be
 * skipped.
 */
export function AiStepPage({ onFinish }: { onFinish: () => Promise<void> }) {
  const { t } = useTranslation();
  const { ready, activated, account, busy, appInfo, error, activate, refresh } = useAccountStore();
  const backedUp = useConfigStore((s) => s.config.account.keyBackupConfirmedAt !== null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [retrying, setRetrying] = useState(false);
  const [finishing, setFinishing] = useState<"idle" | "saving" | "error">("idle");

  const supported = inappSupported(appInfo);
  const usable = supported && activated && !account?.blocked;
  const empty = !account || account.balanceUsd <= 0;

  const retry = async () => {
    setRetrying(true);
    try {
      await activate();
      await ensureDefaultModel();
    } catch {
      // The inactive notice stays up; it already says what to check.
    } finally {
      setRetrying(false);
    }
  };

  const finish = async () => {
    setFinishing("saving");
    try {
      await onFinish();
    } catch {
      setFinishing("error");
    }
  };

  const closeDialog = () => {
    setDialog(null);
    void refresh();
  };

  return (
    <>
      <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{t("onboardingAi.title")}</h1>
      <p className="mt-2 text-base text-[var(--color-text-secondary)] leading-relaxed">
        {t("onboardingAi.lead")}
      </p>

      {/* Where the account stands. One of these is always shown. */}
      <section
        aria-live="polite"
        className="mt-6 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-card)] px-5 py-4"
      >
        {!supported ? (
          <p className="text-sm text-[var(--color-warning)] leading-relaxed">{t("onboardingAi.status.unsupported")}</p>
        ) : !ready || (busy && !activated) ? (
          <p className="text-sm text-[var(--color-text-secondary)]">{t("onboardingAi.status.loading")}</p>
        ) : !activated ? (
          <div className="space-y-3">
            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("onboardingAi.status.inactive")}</p>
            <Button variant="outline" disabled={retrying} onClick={() => void retry()} className="h-11 px-4">
              {retrying ? t("onboardingAi.status.retrying") : t("onboardingAi.status.retry")}
            </Button>
          </div>
        ) : account?.blocked ? (
          <p className="text-sm text-[var(--color-error)] leading-relaxed">
            {t("onboardingAi.status.blocked")}
            {account.blockedReason ? ` (${account.blockedReason})` : ""}
          </p>
        ) : account ? (
          <div>
            <p className="text-sm text-[var(--color-text-muted)]">{t("onboardingAi.balance")}</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-[var(--color-text-primary)]">
              {formatUsd(account.balanceUsd)}
              <span className="ml-2 text-base font-medium text-[var(--color-text-secondary)]">
                {formatIdr(account.balanceIdr)}
              </span>
            </p>
          </div>
        ) : (
          <p className="text-sm text-[var(--color-text-secondary)]">
            {error ? t("onboardingAi.status.balanceFailed") : t("onboardingAi.status.balanceLoading")}
          </p>
        )}
      </section>

      <ol className="mt-8 space-y-8">
        <Step n={1} title={t("onboardingAi.steps.backup.title")} body={t("onboardingAi.steps.backup.body")}>
          {backedUp && (
            <p className="text-sm text-[var(--color-success)]">{t("onboardingAi.steps.backup.done")}</p>
          )}
          <Button
            variant={backedUp ? "outline" : "default"}
            disabled={!usable}
            onClick={() => setDialog("backup")}
            className="h-11 px-5"
          >
            {backedUp ? t("onboardingAi.steps.backup.again") : t("onboardingAi.steps.backup.action")}
          </Button>
        </Step>

        <Step n={2} title={t("onboardingAi.steps.topup.title")} body={t("onboardingAi.steps.topup.body")}>
          <Button
            variant={backedUp ? "default" : "outline"}
            disabled={!usable}
            onClick={() => setDialog("topup")}
            className="h-11 px-5"
          >
            {t("onboardingAi.steps.topup.action")}
          </Button>
        </Step>
      </ol>

      <p className="mt-8 text-sm text-[var(--color-text-secondary)]">
        {t("onboardingAi.restoreQuestion")}{" "}
        <button
          type="button"
          disabled={!supported || busy}
          onClick={() => setDialog("restore")}
          className="inline-flex min-h-11 items-center font-medium text-[var(--color-accent)] underline underline-offset-4 hover:no-underline disabled:opacity-50 disabled:no-underline cursor-pointer disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] rounded-sm"
        >
          {t("onboardingAi.restore")}
        </button>
      </p>

      <div className="mt-8 border-t border-[var(--color-border-light)] pt-6">
        {finishing === "error" && (
          <p role="alert" className="mb-3 text-sm text-[var(--color-error)]">
            {t("onboarding.finishFailed")}
          </p>
        )}
        <Button
          size="lg"
          disabled={finishing === "saving"}
          onClick={() => void finish()}
          className="h-12 px-6 text-base font-semibold"
        >
          {finishing === "saving" ? t("onboarding.finishing") : t("onboarding.finish")}
        </Button>
        {usable && empty && (
          <p className="mt-3 text-sm text-[var(--color-text-muted)] leading-relaxed">{t("onboardingAi.emptyHint")}</p>
        )}
      </div>

      {dialog === "backup" && <AccountKeyDialog mode="export" onClose={closeDialog} />}
      {dialog === "restore" && <AccountKeyDialog mode="restore" onClose={closeDialog} />}
      {dialog === "topup" && <TopupDialog onClose={closeDialog} />}
    </>
  );
}
