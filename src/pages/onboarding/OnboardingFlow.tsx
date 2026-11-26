import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { useConfigStore } from "@/stores/configStore";
import { OnboardingShell, type OnboardingFooter } from "./OnboardingShell";
import { CookiesStepPage } from "./CookiesStepPage";
import { AiStepPage } from "./AiStepPage";
import { ReplizStepPage } from "./ReplizStepPage";

type StepId = "cookies" | "ai" | "repliz";

/**
 * The first-launch setup after the language picker: YouTube cookies, the AI
 * balance, then Repliz. Users who already run on their own API key skip the AI
 * balance step: it is about the in-app wallet only.
 *
 * Each step reports whether it is done; the flow owns the one forward button,
 * so every step moves on the same way.
 */
export function OnboardingFlow() {
  const { t } = useTranslation();
  const usesInapp = useConfigStore((s) => s.config.ai.source === "inapp");
  const completeOnboarding = useConfigStore((s) => s.completeOnboarding);
  const steps: StepId[] = usesInapp ? ["cookies", "ai", "repliz"] : ["cookies", "repliz"];
  const [index, setIndex] = useState(0);
  // The AI step can always be passed: topping up is optional.
  const [ready, setReady] = useState<Record<StepId, boolean>>({ cookies: false, ai: true, repliz: false });

  const report = useMemo(
    () => ({
      cookies: (r: boolean) => setReady((prev) => (prev.cookies === r ? prev : { ...prev, cookies: r })),
      repliz: (r: boolean) => setReady((prev) => (prev.repliz === r ? prev : { ...prev, repliz: r })),
    }),
    [],
  );

  const current = steps[Math.min(index, steps.length - 1)];
  const isLast = index >= steps.length - 1;
  const following = steps[index + 1];

  const next = () => {
    if (isLast) {
      completeOnboarding().catch(() => toast.error(t("onboarding.finishFailed")));
      return;
    }
    setIndex(index + 1);
    window.scrollTo({ top: 0 });
  };

  const back =
    index > 0
      ? () => {
          setIndex(index - 1);
          window.scrollTo({ top: 0 });
        }
      : undefined;

  const followingTitle =
    following === "ai" ? t("onboardingAi.title") : following === "repliz" ? t("onboardingRepliz.title") : "";

  const skip: OnboardingFooter["skip"] = ready[current]
    ? undefined
    : current === "cookies"
      ? { label: t("onboardingCookies.later") }
      : current === "repliz"
        ? { label: t("onboardingRepliz.skip") }
        : undefined;

  const footer: OnboardingFooter = {
    upNext: isLast ? t("onboarding.lastStep") : t("onboarding.upNext", { title: followingTitle }),
    cta: isLast ? t("onboarding.finish") : t("onboarding.next"),
    canContinue: ready[current],
    onNext: next,
    skip,
  };

  return (
    <OnboardingShell step={index + 1} total={steps.length} onBack={back} footer={footer}>
      {current === "cookies" && <CookiesStepPage onReadyChange={report.cookies} />}
      {current === "ai" && <AiStepPage />}
      {current === "repliz" && <ReplizStepPage onReadyChange={report.repliz} />}
    </OnboardingShell>
  );
}
