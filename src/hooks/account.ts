import { invoke } from "@tauri-apps/api/core";

/**
 * The in-app AI account.
 *
 * Every call here crosses into Rust, which holds the device token in the OS
 * credential store. Nothing in this file ever sees it — except
 * `exportAccountToken`, which is the one deliberate hole, because an account
 * with no server-side recovery has to be portable by hand.
 */

/** What this device holds locally. No network, safe on every launch. */
export interface AccountState {
  activated: boolean;
  accountId: string | null;
  hasInferenceKey: boolean;
}

export interface Membership {
  tier: "REGULAR" | "GOLD";
  lifetimeTopupUsd: number;
  thresholdUsd: number;
  remainingUsd: number;
  groupUrl: string | null;
}

export interface Account {
  accountId: string;
  balanceUsd: number;
  toppedUpUsd: number;
  spentUsd: number;
  balanceIdr: number;
  usdIdrRate: number;
  hasApiKey: boolean;
  membership: Membership;
  blocked: boolean;
  blockedReason: string | null;
}

export interface FeeRate {
  usdIdrRate: number;
  platformFeePercent: number;
  minTopupUsd: number;
  maxTopupUsd: number;
}

export type TopupStatus = "pending" | "paid" | "expired" | "failed" | "cancelled";

export interface Topup {
  id: string;
  status: TopupStatus;
  usdAmount: number;
  idrAmount: number;
  platformFeeIdr: number;
  totalIdr: number;
  /** Raw QRIS payload to render. Null once the invoice is no longer payable. */
  qrString: string | null;
  expiresAt: string | null;
  paidAt: string | null;
  createdAt: string;
}

export interface ModelCapabilities {
  vision: boolean;
  functionCalling: boolean;
  reasoning: boolean;
  promptCaching: boolean;
  streaming: boolean;
  audioInput: boolean;
  audioOutput: boolean;
  pdfInput: boolean;
}

export interface CatalogModel {
  id: string;
  /** The value to send as `model` to the inference endpoint. */
  name: string;
  provider: string;
  mode: string;
  maxInputTokens: number | null;
  maxOutputTokens: number | null;
  inputCostPerToken: number | null;
  outputCostPerToken: number | null;
  inputCostPerSecond: number | null;
  capabilities: ModelCapabilities;
}

export interface UsageLog {
  requestId: string;
  model: string;
  status: "success" | "failure";
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  spendUsd: number;
  startedAt: string;
  endedAt: string;
  durationMs: number;
  errorMessage: string | null;
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface Page<T> {
  data: T[];
  pagination: PaginationMeta;
}

export interface AppInfo {
  minSupportedVersion: string;
  latestVersion: string;
  downloadUrl: string;
  /** Release notes for `latestVersion`, shown in the update dialog. */
  changelog: string | null;
  notice: string | null;
}

export function accountState(): Promise<AccountState> {
  return invoke<AccountState>("account_state");
}

/**
 * Creates the account. Fired automatically on first launch, and again from the
 * retry button when that attempt could not reach the server.
 */
export function registerAccount(
  appVersion: string,
  idempotencyKey: string
): Promise<Account> {
  return invoke<Account>("account_register", { appVersion, idempotencyKey });
}

export function fetchAccount(): Promise<Account> {
  return invoke<Account>("account_me");
}

/**
 * The raw device token, for the Export Account Key screen only.
 *
 * Show it behind an explicit reveal and never log it: anyone holding this
 * string can spend the balance, and it is also the only way to get the balance
 * back after a reinstall.
 */
export function exportAccountToken(): Promise<string> {
  return invoke<string>("account_export_token");
}

/**
 * Writes the key to a file the user chose. Rust holds the secret throughout,
 * so a backup can be saved without ever putting it on screen.
 */
export function exportAccountToFile(path: string): Promise<void> {
  return invoke<void>("account_export_to_file", { path });
}

export function restoreAccount(token: string): Promise<Account> {
  return invoke<Account>("account_restore", { token });
}

/** Detaches the account from this device. The balance stays with the token. */
export function forgetAccount(): Promise<void> {
  return invoke<void>("account_forget");
}

export function fetchFeeRate(): Promise<FeeRate> {
  return invoke<FeeRate>("account_fee_rate");
}

export function fetchModels(): Promise<{ data: CatalogModel[] }> {
  return invoke<{ data: CatalogModel[] }>("account_models");
}

export function createTopup(usdAmount: number): Promise<Topup> {
  return invoke<Topup>("account_topup_create", { usdAmount });
}

/**
 * Polls one invoice. `force` skips the server's 4-second throttle and belongs
 * behind an explicit "I have paid" press, never on the automatic timer.
 */
export function getTopup(topupId: string, force = false): Promise<Topup> {
  return invoke<Topup>("account_topup_get", { topupId, force });
}

export function fetchTopups(page = 1, pageSize = 10): Promise<Page<Topup>> {
  return invoke<Page<Topup>>("account_topups", { page, pageSize });
}

export function fetchUsage(
  startDate: string,
  endDate: string,
  page = 1,
  pageSize = 20
): Promise<Page<UsageLog>> {
  return invoke<Page<UsageLog>>("account_usage", { startDate, endDate, page, pageSize });
}

export function fetchAppInfo(): Promise<AppInfo> {
  return invoke<AppInfo>("account_app_info");
}

/**
 * Errors arrive as `CODE: message`, the same split the API documents for its
 * own envelope plus a few the client raises on its own (NETWORK, KEYSTORE,
 * NO_ACCOUNT, ALREADY_ACTIVATED). Branch on the code, show the message.
 */
export function errorCode(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  const match = raw.match(/^([A-Z_]+):\s/);
  return match ? match[1] : "UNKNOWN";
}

/**
 * The sentence to show a person: no code, no technical tail.
 *
 * Rust appends the failing request as a trailing `[GET /me → 502; ...]`. The
 * pattern refuses to match when that tail itself contains a `[`, which keeps a
 * nested JSON `details` payload from being half-chopped — in that case the
 * whole string is shown instead. Erring toward too much is the right way round
 * for an error message.
 */
export function errorMessage(err: unknown): string {
  return errorDetail(err)
    .replace(/^[A-Z_]+:\s/, "")
    .replace(/\s*\[[^[]*\]$/, "");
}

/** Everything, including the failing request. For logs and bug reports. */
export function errorDetail(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

/**
 * Whether a failed run failed for lack of money.
 *
 * This one does not come through the account API at all — it surfaces from
 * LiteLLM, through the Python worker, as prose. Matching on prose is fragile,
 * so the caller should treat a false negative as an ordinary error rather than
 * relying on this being exhaustive.
 */
export function isOutOfBalance(err: unknown): boolean {
  const raw = (err instanceof Error ? err.message : String(err)).toLowerCase();
  return (
    raw.includes("budget has been exceeded") ||
    raw.includes("exceeded budget") ||
    raw.includes("budget exceeded") ||
    raw.includes("insufficient balance")
  );
}

/** Jakarta calendar date, which is what the usage endpoint means by a date. */
export function jakartaDate(offsetDays = 0): string {
  const now = new Date();
  const jakarta = new Date(now.getTime() + 7 * 60 * 60 * 1000 + offsetDays * 86_400_000);
  return jakarta.toISOString().slice(0, 10);
}
