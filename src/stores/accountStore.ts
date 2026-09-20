import { create } from "zustand";
import {
  accountState,
  errorCode,
  errorMessage,
  fetchAccount,
  fetchAppInfo,
  fetchModels,
  forgetAccount,
  registerAccount,
  restoreAccount,
  type Account,
  type AppInfo,
} from "@/hooks/account";
import { useConfigStore } from "@/stores/configStore";
import { getInstallationId } from "@/hooks/installationId";
import { APP_VERSION } from "@/config/version";
import { compareVersions } from "@/utils/version";

interface AccountStoreState {
  /** False until the first `init` settles, so the sidebar can stay quiet. */
  ready: boolean;
  /** Whether this device holds a token at all. */
  activated: boolean;
  accountId: string | null;
  /** Server-side state. Null when not activated, offline, or not fetched yet. */
  account: Account | null;
  refreshing: boolean;
  busy: boolean;
  /** Last failure from a balance refresh, for a quiet inline note. */
  error: string | null;
  appInfo: AppInfo | null;

  init: () => Promise<void>;
  refresh: () => Promise<void>;
  activate: () => Promise<Account>;
  restore: (token: string) => Promise<Account>;
  forget: () => Promise<void>;
}

let initOnce: Promise<void> | null = null;

type Setter = (partial: Partial<AccountStoreState>) => void;
type Getter = () => AccountStoreState;

/**
 * First-launch provisioning.
 *
 * The account is created here rather than behind a button: the app is meant to
 * work without a signup, and an empty wallet with a Top Up next to it is a
 * clearer invitation than a dead "not active" chip. A failure is not worth
 * reporting — there is nothing the user did wrong and nothing for them to fix
 * — so it simply tries again the next time the app opens.
 */
async function runInit(set: Setter, get: Getter): Promise<void> {
  let state;
  try {
    state = await accountState();
  } catch {
    set({ ready: true });
    return;
  }
  set({ activated: state.activated, accountId: state.accountId, ready: true });

  // The version floor decides whether we are allowed to provision at all, so
  // it has to be known before registering rather than alongside it. Offline
  // leaves it null, which means "no floor" and lets the attempt proceed.
  const appInfo = await fetchAppInfo().catch(() => null);
  if (appInfo) set({ appInfo });

  if (state.activated) {
    await get().refresh();
    return;
  }

  if (!inappSupported(appInfo)) return;

  try {
    await get().activate();
    await ensureDefaultModel();
  } catch {
    // Usually no network on first run. The AI Models page offers a manual
    // retry, and the next launch takes another turn on its own.
  }
}

/**
 * Picks a model if none is chosen yet.
 *
 * Provisioning a wallet and then stopping the first run with "choose a model"
 * would trade one dead end for another, so activation is only finished once
 * there is something to infer with. An existing choice is never overwritten.
 */
export async function ensureDefaultModel(): Promise<void> {
  const store = useConfigStore.getState();
  // The config load races this on startup; wait for it rather than reading a
  // default that is about to be replaced by what is on disk.
  if (!store.loaded) await store.load();
  if (useConfigStore.getState().config.ai.inapp.model.trim()) return;

  const { data } = await fetchModels();
  const first = data.find((model) => model.mode === "chat") ?? data[0];
  if (first) await useConfigStore.getState().setInappModel(first.name);
}

/** Re-reads what the credential store actually holds. */
async function syncLocalState(
  set: (partial: Partial<AccountStoreState>) => void
): Promise<void> {
  try {
    const state = await accountState();
    set({ activated: state.activated, accountId: state.accountId });
  } catch {
    // Leave the last known state alone; a store we cannot read is not a store
    // that is empty.
  }
}

export const useAccountStore = create<AccountStoreState>((set, get) => ({
  ready: false,
  activated: false,
  accountId: null,
  account: null,
  refreshing: false,
  busy: false,
  error: null,
  appInfo: null,

  /**
   * Reads local state, provisions an account if this installation has none,
   * then fills in the balance behind it.
   *
   * Nothing here blocks the app: it is fired and forgotten from the mount
   * effect, so a user on a custom provider, or with no network at all, reaches
   * the Create page exactly as fast as before.
   *
   * Memoised because StrictMode invokes mount effects twice in development,
   * and two concurrent registrations would mint two LiteLLM keys — the
   * idempotency key keeps the *account* single, but key creation has no such
   * protection, and the loser of that race becomes an orphan on the account.
   */
  init: () => {
    if (!initOnce) initOnce = runInit(set, get);
    return initOnce;
  },

  refresh: async () => {
    if (!get().activated) return;
    set({ refreshing: true });
    try {
      const account = await fetchAccount();
      set({ account, error: null });
    } catch (err) {
      // A revoked or missing token is the one case worth surfacing loudly;
      // everything else is a transient the next refresh will clear.
      const code = errorCode(err);
      if (code === "UNAUTHENTICATED") {
        set({ error: errorMessage(err), account: null });
      } else {
        set({ error: errorMessage(err) });
      }
    } finally {
      set({ refreshing: false });
    }
  },

  activate: async () => {
    set({ busy: true });
    try {
      const idempotencyKey = await getInstallationId();
      const account = await registerAccount(APP_VERSION, idempotencyKey);
      set({ account, error: null });
      return account;
    } finally {
      // Registration writes the token before it fetches anything, so a failure
      // in the tail of that call still leaves an account on this device. Read
      // the credential store for the truth rather than inferring it from
      // whether the command threw.
      await syncLocalState(set);
      set({ busy: false });
    }
  },

  restore: async (token: string) => {
    set({ busy: true });
    try {
      const account = await restoreAccount(token);
      set({ account, error: null });
      return account;
    } finally {
      await syncLocalState(set);
      set({ busy: false });
    }
  },

  forget: async () => {
    set({ busy: true });
    try {
      await forgetAccount();
      set({ activated: false, accountId: null, account: null, error: null });
    } finally {
      set({ busy: false });
    }
  },
}));

/**
 * Whether this build is still allowed to use in-app AI.
 *
 * The version floor only ever disables the in-app account and top-ups. Users on
 * their own API key have no relationship with our servers and should not lose
 * the app because we had to pull a release.
 */
export function inappSupported(appInfo: AppInfo | null): boolean {
  if (!appInfo?.minSupportedVersion) return true;
  return compareVersions(APP_VERSION, appInfo.minSupportedVersion) >= 0;
}
