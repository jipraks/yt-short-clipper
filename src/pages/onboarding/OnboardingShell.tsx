import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Wordmark } from "@/components/brand/Wordmark";

/** The frame every setup step shares: wordmark, position, and a way back. */
export function OnboardingShell({
  step,
  total,
  onBack,
  children,
}: {
  step: number;
  total: number;
  onBack?: () => void;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <main className="min-h-screen bg-[var(--color-bg-secondary)] px-4 py-10">
      <div className="mx-auto w-full max-w-[720px]">
        <div className="flex items-center justify-between gap-4">
          <Wordmark className="text-2xl" />
          {total > 1 && (
            <p className="text-sm text-[var(--color-text-muted)] tabular-nums">
              {t("onboarding.stepOf", { n: step, total })}
            </p>
          )}
        </div>
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="mt-8 -ml-2 inline-flex h-11 items-center rounded-[var(--radius-sm)] px-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] cursor-pointer"
          >
            {t("onboarding.back")}
          </button>
        )}
        <div className={onBack ? "mt-2" : "mt-10"}>{children}</div>
      </div>
    </main>
  );
}
