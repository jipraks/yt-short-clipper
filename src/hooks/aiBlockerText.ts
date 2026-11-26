import type { TFunction } from "i18next";
import type { AIBlocker } from "@/hooks/aiRuntime";

/** Why the AI cannot run right now, in the user's language. */
export function aiBlockerText(t: TFunction, blocker: AIBlocker): string {
  return blocker.kind === "account-blocked" ? blocker.detail : t(`renderPage.blocker.${blocker.kind}`);
}
