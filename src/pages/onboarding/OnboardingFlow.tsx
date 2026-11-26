import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { useConfigStore } from "@/stores/configStore";
import { OnboardingShell } from "./OnboardingShell";
import { CookiesStepPage } from "./CookiesStepPage";
import { AiStepPage } from "./AiStepPage";

type StepId = "cookies" | "ai";

/**
 * The first-launch setup after the language picker. Users who already run on
 * their own API key skip the AI balance step: it is about the in-app wallet
 * only, and nothing in it applies to them.
 */
export function OnboardingFlow() {
  const { t } = useTranslation();
  const usesInapp = useConfigStore((s) => s.config.ai.source === "inapp");
  const completeOnboarding = useConfigStore((s) => s.completeOnboarding);
  const steps: StepId[] = usesInapp ? ["cookies", "ai"] : ["cookies"];
  const [index, setIndex] = useState(0);

  const current = steps[Math.min(index, steps.length - 1)];
  const isLast = index >= steps.length - 1;

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

  return (
    <OnboardingShell step={index + 1} total={steps.length} onBack={back}>
      {current === "cookies" && <CookiesStepPage onNext={next} isLast={isLast} />}
      {current === "ai" && <AiStepPage onFinish={completeOnboarding} />}
    </OnboardingShell>
  );
}
