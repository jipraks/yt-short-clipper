import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { save } from "@tauri-apps/plugin-dialog";
import { AlertTriangle, Check, Copy, Download, Eye, EyeOff, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { errorMessage, exportAccountToFile, exportAccountToken } from "@/hooks/account";
import { useAccountStore } from "@/stores/accountStore";
import { useConfigStore } from "@/stores/configStore";
import { formatUsd } from "@/utils/format";

type Mode = "export" | "restore";

interface AccountKeyDialogProps {
  mode: Mode;
  /** Shown on the export screen when a top-up is waiting on the backup. */
  requireConfirm?: boolean;
  onClose: () => void;
  /** Fired once the user confirms the backup, or a restore succeeds. */
  onDone?: () => void;
}

/**
 * Same shape check the Rust side runs before any request, so an obviously
 * wrong paste gets a plain-language reason instead of a backend message.
 */
function looksLikeToken(token: string): boolean {
  const parts = token.split(".");
  return token.startsWith("ytclip_dev_") && parts.length === 2 && parts.every((part) => part !== "");
}

export function AccountKeyDialog({ mode, requireConfirm = false, onClose, onDone }: AccountKeyDialogProps) {
  const { t } = useTranslation();
  return (
    <Modal
      title={mode === "export" ? t("billing.accountKey.exportTitle") : t("billing.accountKey.restoreTitle")}
      closeLabel={t("billing.accountKey.close")}
      onClose={onClose}
      className="max-w-lg max-h-[90vh] overflow-y-auto"
    >
      {(close) =>
        mode === "export" ? (
          <ExportPanel requireConfirm={requireConfirm} onClose={close} onDone={onDone} />
        ) : (
          <RestorePanel onClose={close} onDone={onDone} />
        )
      }
    </Modal>
  );
}

/** The warning block both panels lead with. Worth repeating; nobody reads it twice. */
function DangerNote({ children }: { children: ReactNode }) {
  return (
    <div className="mt-4 flex items-start gap-3 rounded-[var(--radius)] border border-[var(--color-error)]/30 bg-[var(--color-error-bg)] p-4">
      <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-error)]" />
      <div className="space-y-2 text-sm leading-relaxed text-[var(--color-text-secondary)]">{children}</div>
    </div>
  );
}

function ExportPanel({
  requireConfirm,
  onClose,
  onDone,
}: {
  requireConfirm: boolean;
  onClose: () => void;
  onDone?: () => void;
}) {
  const { t } = useTranslation();
  const accountId = useAccountStore((s) => s.accountId);
  const confirmKeyBackup = useConfigStore((s) => s.confirmKeyBackup);

  const [token, setToken] = useState<string | null>(null);
  const [revealing, setRevealing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  // Fetched only on demand. A key that is never revealed is never on screen,
  // which matters for an audience that records its screen a lot.
  const reveal = async () => {
    if (token) {
      setToken(null);
      return;
    }
    setRevealing(true);
    try {
      setToken(await exportAccountToken());
    } catch (err) {
      toast.error(t("billing.accountKey.export.revealFailed", { reason: errorMessage(err) }));
    } finally {
      setRevealing(false);
    }
  };

  const copy = async () => {
    try {
      const value = token ?? (await exportAccountToken());
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success(t("billing.accountKey.export.copyDone"));
    } catch (err) {
      toast.error(t("billing.accountKey.export.copyFailed", { reason: errorMessage(err) }));
    }
  };

  const saveToFile = async () => {
    setSaving(true);
    try {
      const path = await save({
        title: t("billing.accountKey.export.saveDialogTitle"),
        defaultPath: `ytclip-account-key-${accountId ?? "backup"}.txt`,
        filters: [{ name: t("billing.accountKey.export.fileFilter"), extensions: ["txt"] }],
      });
      if (!path) return;
      await exportAccountToFile(path);
      toast.success(t("billing.accountKey.export.saved"));
    } catch (err) {
      toast.error(t("billing.accountKey.export.saveFailed", { reason: errorMessage(err) }));
    } finally {
      setSaving(false);
    }
  };

  const confirm = async () => {
    try {
      await confirmKeyBackup();
      // A caller that passed `onDone` has somewhere to go next: the top-up
      // flow continues into its amount step rather than closing on the user
      // who just pressed "Continue".
      if (onDone) onDone();
      else onClose();
    } catch (err) {
      toast.error(t("billing.accountKey.export.confirmFailed", { reason: errorMessage(err) }));
    }
  };

  return (
    <>
      <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {t("billing.accountKey.export.intro")}
      </p>

      <DangerNote>
        <p>
          <strong className="font-semibold text-[var(--color-text-primary)]">
            {t("billing.accountKey.export.warnSpendTitle")}
          </strong>{" "}
          {t("billing.accountKey.export.warnSpendBody")}
        </p>
        <p>
          <strong className="font-semibold text-[var(--color-text-primary)]">
            {t("billing.accountKey.export.warnRecoverTitle")}
          </strong>{" "}
          {t("billing.accountKey.export.warnRecoverBody")}
        </p>
        <p>
          <strong className="font-semibold text-[var(--color-text-primary)]">
            {t("billing.accountKey.export.warnRefund")}
          </strong>
        </p>
      </DangerNote>

      {accountId && (
        <p className="mt-4 text-xs text-[var(--color-text-muted)]">
          {t("billing.accountKey.export.accountId")}:{" "}
          <span className="font-mono text-[var(--color-text-secondary)]">{accountId}</span>.{" "}
          {t("billing.accountKey.export.accountIdNote")}
        </p>
      )}

      <div className="mt-5 mb-1.5 flex items-center justify-between gap-2">
        <span id="account-key-label" className="text-xs font-medium text-[var(--color-text-muted)]">
          {t("billing.accountKey.export.keyLabel")}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void reveal()}
          disabled={revealing}
          aria-pressed={token !== null}
          aria-label={token ? t("billing.accountKey.export.hideAria") : t("billing.accountKey.export.showAria")}
          className="-mr-2 h-9 gap-1.5 px-3 text-sm"
        >
          {revealing ? (
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          ) : token ? (
            <EyeOff aria-hidden className="h-4 w-4" />
          ) : (
            <Eye aria-hidden className="h-4 w-4" />
          )}
          {token ? t("billing.accountKey.export.hide") : t("billing.accountKey.export.show")}
        </Button>
      </div>
      <div
        aria-labelledby="account-key-label"
        className="flex min-h-[48px] items-center break-all rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-input)] px-4 py-3 font-mono text-xs text-[var(--color-text-primary)]"
      >
        {token ?? (
          <span className="font-sans text-sm text-[var(--color-text-muted)]">
            {t("billing.accountKey.export.hiddenNote")}
          </span>
        )}
      </div>

      <div className="mt-3 flex gap-2">
        <Button variant="outline" onClick={() => void copy()} className="h-10 flex-1 gap-2">
          {copied ? (
            <Check aria-hidden className="h-4 w-4 text-[var(--color-success)]" />
          ) : (
            <Copy aria-hidden className="h-4 w-4" />
          )}
          {copied ? t("billing.accountKey.export.copied") : t("billing.accountKey.export.copy")}
        </Button>
        <Button variant="outline" onClick={() => void saveToFile()} disabled={saving} className="h-10 flex-1 gap-2">
          {saving ? <Loader2 aria-hidden className="h-4 w-4 animate-spin" /> : <Download aria-hidden className="h-4 w-4" />}
          {t("billing.accountKey.export.saveFile")}
        </Button>
      </div>

      {requireConfirm ? (
        <>
          <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4 text-sm leading-relaxed text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-0.5 h-4 w-4 shrink-0 cursor-pointer accent-[var(--color-accent-fill)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
            />
            <span>{t("billing.accountKey.export.confirmLabel")}</span>
          </label>
          <Button onClick={() => void confirm()} disabled={!acknowledged} className="mt-4 h-11 w-full">
            {t("billing.accountKey.export.continue")}
          </Button>
        </>
      ) : (
        <Button onClick={onClose} className="mt-6 h-11 w-full">
          {t("billing.accountKey.export.done")}
        </Button>
      )}
    </>
  );
}

function RestorePanel({ onClose, onDone }: { onClose: () => void; onDone?: () => void }) {
  const { t } = useTranslation();
  const { activated, account, restore, busy } = useAccountStore();
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    const value = token.trim();
    if (!value) {
      setError(t("billing.accountKey.restore.errorEmpty"));
      return;
    }
    if (!looksLikeToken(value)) {
      setError(t("billing.accountKey.restore.errorShape"));
      return;
    }
    setError(null);
    try {
      const restored = await restore(value);
      toast.success(t("billing.accountKey.restore.success", { balance: formatUsd(restored.balanceUsd) }));
      onDone?.();
      onClose();
    } catch (err) {
      setError(t("billing.accountKey.restore.errorFailed", { reason: errorMessage(err) }));
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {t("billing.accountKey.restore.intro")}
      </p>

      {activated && (
        <DangerNote>
          <p>
            {account
              ? t("billing.accountKey.restore.replaceWarnBalance", { balance: formatUsd(account.balanceUsd) })
              : t("billing.accountKey.restore.replaceWarn")}
          </p>
        </DangerNote>
      )}

      <label htmlFor="restore-key" className="mt-5 mb-1.5 block text-xs font-medium text-[var(--color-text-muted)]">
        {t("billing.accountKey.restore.keyLabel")}
      </label>
      <Input
        id="restore-key"
        value={token}
        onChange={(e) => {
          setToken(e.target.value);
          if (error) setError(null);
        }}
        placeholder={t("billing.accountKey.restore.placeholder")}
        className="font-mono text-xs"
        autoComplete="off"
        spellCheck={false}
        aria-invalid={error !== null}
        aria-describedby={error ? "restore-key-error" : "restore-key-hint"}
      />
      {error ? (
        <p id="restore-key-error" role="alert" className="mt-2 text-xs leading-relaxed text-[var(--color-error)] break-words">
          {error}
        </p>
      ) : (
        <p id="restore-key-hint" className="mt-2 text-xs text-[var(--color-text-muted)]">
          {t("billing.accountKey.restore.hint")}
        </p>
      )}

      <div className="mt-6 flex gap-2">
        <Button type="button" variant="outline" onClick={onClose} className="h-11 flex-1">
          {t("billing.accountKey.restore.cancel")}
        </Button>
        <Button type="submit" disabled={busy} className="h-11 flex-1 gap-2">
          {busy && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
          {busy ? t("billing.accountKey.restore.restoring") : t("billing.accountKey.restore.submit")}
        </Button>
      </div>
    </form>
  );
}
