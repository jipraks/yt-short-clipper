import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/brand/Wordmark";

export interface OnboardingFooter {
  /** What the next step is, or that this is the last one: the reason to click. */
  upNext: string;
  cta: string;
  canContinue: boolean;
  onNext: () => void;
  /** A quiet way past a step that is not done yet. */
  skip?: { label: string };
}

/**
 * The frame every setup step shares: wordmark, position, a way back, and the
 * bar that moves the user forward. The bar sticks to the bottom so the one red
 * call to action is always in view and never mistaken for a button inside the
 * step.
 */
export function OnboardingShell({
  step,
  total,
  onBack,
  footer,
  children,
}: {
  step: number;
  total: number;
  onBack?: () => void;
  footer: OnboardingFooter;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <main className="min-h-screen bg-[var(--color-bg-secondary)] px-4 pt-10">
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

      <div className="sticky bottom-0 -mx-4 mt-12 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-4">
        <div className="mx-auto flex w-full max-w-[720px] flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-sm text-[var(--color-text-secondary)]">{footer.upNext}</p>
            {footer.skip && (
              <button
                type="button"
                onClick={footer.onNext}
                className="inline-flex min-h-11 items-center text-sm text-[var(--color-text-muted)] underline underline-offset-4 hover:text-[var(--color-text-secondary)] cursor-pointer rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
              >
                {footer.skip.label}
              </button>
            )}
          </div>
          <Button
            size="lg"
            disabled={!footer.canContinue}
            onClick={footer.onNext}
            className="h-14 w-full shrink-0 gap-2 px-8 text-base font-bold sm:w-auto"
          >
            {footer.cta}
            {/* The arrow says "forward to the next screen"; it is on this button only. */}
            <ArrowRight aria-hidden className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </main>
  );
}
