import type { AISettings, AISource } from "@/hooks/appConfig";
import type { Account } from "@/hooks/account";

/**
 * What the sidecar is handed for a run.
 *
 * For `inapp` the credentials are deliberately absent — Rust fills `api_key`
 * and `base_url` from the OS credential store on the way through, so the key
 * never exists in the renderer. For `custom` they are what the user typed.
 */
export interface AIRequestSettings {
  source: AISource;
  model: string;
  api_key?: string;
  base_url?: string;
  system_message?: string;
  temperature?: number;
}

export type AIBlocker =
  | { kind: "not-activated" }
  | { kind: "no-model" }
  | { kind: "no-key" }
  | { kind: "no-balance" }
  | { kind: "account-blocked"; detail: string }
  | { kind: "version" };

export interface AIContext {
  activated: boolean;
  account: Account | null;
  /** False when this build is below the server's minimum for in-app AI. */
  inappSupported: boolean;
}

/**
 * The single answer to "can we run AI right now", so the three call sites stop
 * each inventing their own half of the check.
 *
 * Returns null when everything is in place. The balance check is deliberately
 * here rather than only at the error boundary: a run that dies four clips in
 * because the wallet was already empty wastes the user's download, not just
 * their time.
 */
export function aiBlocker(ai: AISettings, context: AIContext): AIBlocker | null {
  if (ai.source === "custom") {
    if (!ai.custom.apiKey.trim()) return { kind: "no-key" };
    if (!ai.custom.model.trim()) return { kind: "no-model" };
    return null;
  }

  if (!context.inappSupported) return { kind: "version" };
  if (!context.activated) return { kind: "not-activated" };
  if (context.account?.blocked) {
    return {
      kind: "account-blocked",
      detail: context.account.blockedReason ?? "This account has been disabled.",
    };
  }
  if (!ai.inapp.model.trim()) return { kind: "no-model" };
  // A null account means we could not reach the server; let the run try rather
  // than blocking on our own ignorance.
  if (context.account && context.account.balanceUsd <= 0) return { kind: "no-balance" };
  return null;
}

export function blockerMessage(blocker: AIBlocker): string {
  switch (blocker.kind) {
    case "not-activated":
      return "In-app AI is not active yet. Activate it, or switch to your own API key.";
    case "no-model":
      return "Choose a model first.";
    case "no-key":
      return "Configure the AI provider first.";
    case "no-balance":
      return "Your balance is empty. Top up to keep generating.";
    case "account-blocked":
      return blocker.detail;
    case "version":
      return "This version is too old for in-app AI. Update the app, or use your own API key.";
  }
}

export function buildAIRequest(ai: AISettings): AIRequestSettings {
  if (ai.source === "custom") {
    return {
      source: "custom",
      model: ai.custom.model,
      api_key: ai.custom.apiKey,
      base_url: ai.custom.baseUrl,
      system_message: ai.systemMessage,
    };
  }

  return {
    source: "inapp",
    model: ai.inapp.model,
    system_message: ai.systemMessage,
  };
}

/** The model actually in use, for display. */
export function activeModel(ai: AISettings): string {
  return ai.source === "inapp" ? ai.inapp.model : ai.custom.model;
}
