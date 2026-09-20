import { useState, type ReactNode } from "react";
import { save } from "@tauri-apps/plugin-dialog";
import {
  AlertTriangle,
  Check,
  Copy,
  Download,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  errorMessage,
  exportAccountToFile,
  exportAccountToken,
} from "@/hooks/account";
import { useAccountStore } from "@/stores/accountStore";
import { useConfigStore } from "@/stores/configStore";

type Mode = "export" | "restore";

interface AccountKeyDialogProps {
  mode: Mode;
  /** Shown on the export screen when a top-up is waiting on the backup. */
  requireConfirm?: boolean;
  onClose: () => void;
  /** Fired once the user confirms the backup, or a restore succeeds. */
  onDone?: () => void;
}

export function AccountKeyDialog({
  mode,
  requireConfirm = false,
  onClose,
  onDone,
}: AccountKeyDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="w-5 h-5 text-[var(--color-accent)]" />
              {mode === "export" ? "Account Key" : "Restore Account"}
            </CardTitle>
            <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {mode === "export" ? (
            <ExportPanel requireConfirm={requireConfirm} onClose={onClose} onDone={onDone} />
          ) : (
            <RestorePanel onClose={onClose} onDone={onDone} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/** The warning block both panels lead with. Worth repeating; nobody reads it twice. */
function DangerNote({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] border border-[var(--color-error)]/30">
      <AlertTriangle className="w-4 h-4 text-[var(--color-error)] shrink-0 mt-0.5" />
      <div className="text-xs text-[var(--color-text-secondary)] space-y-1.5">{children}</div>
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
      toast.error(errorMessage(err));
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
      toast.success("Account key copied");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const saveToFile = async () => {
    setSaving(true);
    try {
      const path = await save({
        title: "Save account key",
        defaultPath: `ytclip-account-key-${accountId ?? "backup"}.txt`,
        filters: [{ name: "Text", extensions: ["txt"] }],
      });
      if (!path) return;
      await exportAccountToFile(path);
      toast.success("Account key saved");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const confirm = async () => {
    try {
      await confirmKeyBackup();
      // A caller that passed `onDone` has somewhere to go next — the top-up
      // flow continues into its amount step rather than closing on the user
      // who just pressed "Continue".
      if (onDone) onDone();
      else onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <DangerNote>
        <p>
          <strong>Anyone who has this key can spend your balance.</strong> Do not
          share it, and do not leave it on screen while recording.
        </p>
        <p>
          <strong>This is the only way to recover your balance.</strong> If you
          lose it — reinstall, new laptop, dead disk — the balance is gone for
          good. Nobody can restore it, support included.
        </p>
        <p>
          <strong>Top-ups are not refundable.</strong>
        </p>
      </DangerNote>

      {accountId && (
        <div className="text-xs text-[var(--color-text-muted)]">
          Account ID: <span className="font-mono">{accountId}</span> — safe to
          quote to support.
        </div>
      )}

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-[var(--color-text-secondary)]">
            Your account key
          </label>
          <Button variant="ghost" size="sm" onClick={reveal} disabled={revealing}>
            {revealing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : token ? (
              <EyeOff className="w-3.5 h-3.5" />
            ) : (
              <Eye className="w-3.5 h-3.5" />
            )}
            {token ? "Hide" : "Show"}
          </Button>
        </div>
        <div className="px-3 py-2.5 rounded-[var(--radius-sm)] bg-[var(--color-bg-secondary)] border border-[var(--color-border-light)] font-mono text-xs break-all text-[var(--color-text-primary)] min-h-[44px] flex items-center">
          {token ?? "••••••••••••••••••••••••••••••••••••••••"}
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={copy} className="flex-1 gap-2">
          {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          Copy
        </Button>
        <Button variant="outline" onClick={saveToFile} disabled={saving} className="flex-1 gap-2">
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
          Save to file
        </Button>
      </div>

      {requireConfirm ? (
        <>
          <label className="flex items-start gap-2.5 text-sm text-[var(--color-text-secondary)] cursor-pointer">
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              className="mt-0.5 w-4 h-4 accent-[var(--color-accent)] cursor-pointer"
            />
            <span>
              I have saved my account key somewhere safe, and I understand that
              losing it means losing the balance permanently.
            </span>
          </label>
          <Button onClick={confirm} disabled={!acknowledged} className="w-full">
            Continue to top up
          </Button>
        </>
      ) : (
        <Button variant="outline" onClick={onClose} className="w-full">
          Done
        </Button>
      )}
    </div>
  );
}

function RestorePanel({ onClose, onDone }: { onClose: () => void; onDone?: () => void }) {
  const { activated, account, restore, busy } = useAccountStore();
  const [token, setToken] = useState("");

  const submit = async () => {
    if (!token.trim()) {
      toast.error("Paste your account key first");
      return;
    }
    try {
      const restored = await restore(token.trim());
      toast.success(`Account restored — balance $${restored.balanceUsd.toFixed(2)}`);
      onDone?.();
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--color-text-secondary)]">
        Paste the account key you exported from your other installation. The
        balance travels with the key.
      </p>

      {activated && (
        <DangerNote>
          <p>
            This device already has an account
            {account ? ` with $${account.balanceUsd.toFixed(2)} on it` : ""}.
            Restoring another key detaches it from this device — make sure you
            have exported its key first, or that balance becomes unreachable.
          </p>
        </DangerNote>
      )}

      <div className="space-y-2">
        <label className="text-sm font-medium text-[var(--color-text-secondary)]">
          Account key
        </label>
        <Input
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="ytclip_dev_..."
          className="font-mono text-xs"
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={onClose} className="flex-1">
          Cancel
        </Button>
        <Button onClick={submit} disabled={busy} className="flex-1 gap-2">
          {busy && <Loader2 className="w-4 h-4 animate-spin" />}
          Restore
        </Button>
      </div>
    </div>
  );
}
