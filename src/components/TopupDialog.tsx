import { useCallback, useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  QrCode,
  RefreshCw,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { AccountKeyDialog } from "@/components/AccountKeyDialog";
import {
  createTopup,
  errorMessage,
  fetchFeeRate,
  getTopup,
  type FeeRate,
  type Topup,
} from "@/hooks/account";
import { useAccountStore } from "@/stores/accountStore";
import { useConfigStore } from "@/stores/configStore";
import { countdownTo, formatIdr, formatUsd } from "@/utils/format";

/** How often the open dialog asks the server. The API throttles at 4s anyway. */
const POLL_MS = 4000;

const QUICK_AMOUNTS = [5, 10, 25, 50];

interface TopupDialogProps {
  onClose: () => void;
}

export function TopupDialog({ onClose }: TopupDialogProps) {
  const backedUp = useConfigStore((s) => s.config.account.keyBackupConfirmedAt);
  const [topup, setTopup] = useState<Topup | null>(null);

  // No money goes in before the only key to it is somewhere safe. The server
  // keeps no recovery path, so this is the last point where we can insist.
  if (!backedUp) {
    return (
      <AccountKeyDialog
        mode="export"
        requireConfirm
        onClose={onClose}
        // Confirming writes the timestamp to config, which re-renders this
        // component straight into the amount step. Nothing else to do here.
        onDone={() => undefined}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-w-md w-full max-h-[90vh] overflow-y-auto">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <QrCode className="w-5 h-5 text-[var(--color-accent)]" />
              Top Up Balance
            </CardTitle>
            <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {topup ? (
            <InvoicePanel
              topup={topup}
              onReplace={() => setTopup(null)}
              onClose={onClose}
            />
          ) : (
            <AmountPanel onCreated={setTopup} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function AmountPanel({ onCreated }: { onCreated: (topup: Topup) => void }) {
  const [rate, setRate] = useState<FeeRate | null>(null);
  const [amount, setAmount] = useState(10);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchFeeRate()
      .then((value) => {
        setRate(value);
        setAmount((current) =>
          Math.min(Math.max(current, value.minTopupUsd), value.maxTopupUsd)
        );
      })
      .catch((err) => toast.error(errorMessage(err)));
  }, []);

  // Quoted locally so dragging the amount does not cost a request per
  // keystroke. The invoice the server issues is the one that counts.
  const idrAmount = rate ? Math.round(amount * rate.usdIdrRate) : null;
  const feeIdr =
    rate && idrAmount !== null
      ? Math.round((idrAmount * rate.platformFeePercent) / 100)
      : null;
  const totalIdr = idrAmount !== null && feeIdr !== null ? idrAmount + feeIdr : null;

  const withinRange =
    !rate || (amount >= rate.minTopupUsd && amount <= rate.maxTopupUsd);

  const create = async () => {
    setCreating(true);
    try {
      onCreated(await createTopup(amount));
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium text-[var(--color-text-secondary)]">
          Amount (USD)
        </label>
        <Input
          type="number"
          value={amount}
          min={rate?.minTopupUsd ?? 1}
          max={rate?.maxTopupUsd ?? 1000}
          step={1}
          onChange={(e) => setAmount(Math.floor(Number(e.target.value) || 0))}
        />
        <div className="flex gap-2">
          {QUICK_AMOUNTS.filter(
            (value) =>
              !rate || (value >= rate.minTopupUsd && value <= rate.maxTopupUsd)
          ).map((value) => (
            <Button
              key={value}
              variant={amount === value ? "secondary" : "outline"}
              size="sm"
              onClick={() => setAmount(value)}
              className="flex-1"
            >
              ${value}
            </Button>
          ))}
        </div>
        {rate && !withinRange && (
          <p className="text-xs text-[var(--color-error)]">
            Choose between {formatUsd(rate.minTopupUsd)} and{" "}
            {formatUsd(rate.maxTopupUsd)}.
          </p>
        )}
      </div>

      <div className="rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-secondary)] p-3 space-y-1.5 text-sm">
        {rate ? (
          <>
            <Row label={`Credit (${formatUsd(amount)})`} value={formatIdr(idrAmount ?? 0)} />
            <Row
              label={`Payment fee (${rate.platformFeePercent}%)`}
              value={formatIdr(feeIdr ?? 0)}
            />
            <div className="border-t border-[var(--color-border-light)] pt-1.5">
              <Row label="Total to pay" value={formatIdr(totalIdr ?? 0)} strong />
            </div>
            <p className="text-[11px] text-[var(--color-text-muted)] pt-1">
              Rate: {formatIdr(rate.usdIdrRate)} per $1. The final amount is fixed
              when the invoice is issued.
            </p>
          </>
        ) : (
          <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading rate...
          </div>
        )}
      </div>

      <Button
        onClick={create}
        disabled={creating || !rate || !withinRange}
        className="w-full gap-2"
      >
        {creating && <Loader2 className="w-4 h-4 animate-spin" />}
        Create QRIS invoice
      </Button>
    </div>
  );
}

function InvoicePanel({
  topup: initial,
  onReplace,
  onClose,
}: {
  topup: Topup;
  onReplace: () => void;
  onClose: () => void;
}) {
  const refreshAccount = useAccountStore((s) => s.refresh);
  const [topup, setTopup] = useState(initial);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [countdown, setCountdown] = useState(() => countdownTo(initial.expiresAt));

  const settled = topup.status !== "pending";
  // Held in a ref so the poll loop does not restart every time state moves.
  const settledRef = useRef(settled);
  settledRef.current = settled;

  useEffect(() => {
    if (!topup.qrString) {
      setQrDataUrl(null);
      return;
    }
    QRCode.toDataURL(topup.qrString, { width: 320, margin: 1 })
      .then(setQrDataUrl)
      .catch(() => setQrDataUrl(null));
  }, [topup.qrString]);

  const poll = useCallback(
    async (force: boolean) => {
      try {
        const next = await getTopup(topup.id, force);
        setTopup(next);
        if (next.status === "paid") {
          // The credit is already applied by the time this returns.
          void refreshAccount();
        }
        return next;
      } catch (err) {
        if (force) toast.error(errorMessage(err));
        return null;
      }
    },
    [topup.id, refreshAccount]
  );

  useEffect(() => {
    if (settled) return;
    const timer = setInterval(() => {
      if (!settledRef.current) void poll(false);
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [poll, settled]);

  useEffect(() => {
    if (settled) return;
    const timer = setInterval(() => setCountdown(countdownTo(topup.expiresAt)), 1000);
    return () => clearInterval(timer);
  }, [topup.expiresAt, settled]);

  const checkNow = async () => {
    setChecking(true);
    try {
      const next = await poll(true);
      if (next && next.status === "pending") {
        toast.info("Payment not received yet. Give it a moment and try again.");
      }
    } finally {
      setChecking(false);
    }
  };

  if (topup.status === "paid") {
    return (
      <div className="space-y-4 text-center py-2">
        <CheckCircle2 className="w-12 h-12 text-[var(--color-success)] mx-auto" />
        <div>
          <p className="font-semibold text-[var(--color-text-primary)]">
            {formatUsd(topup.usdAmount)} added
          </p>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Invoice {topup.id}
          </p>
        </div>
        <Button onClick={onClose} className="w-full">
          Done
        </Button>
      </div>
    );
  }

  if (settled) {
    return (
      <div className="space-y-4">
        <div className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--color-warning-bg)] border border-[var(--color-warning)]/30">
          <AlertTriangle className="w-4 h-4 text-[var(--color-warning)] shrink-0 mt-0.5" />
          <p className="text-xs text-[var(--color-text-secondary)]">
            {topup.status === "expired"
              ? "This QR code is no longer payable. Nothing was charged."
              : `This invoice ended as "${topup.status}". Nothing was charged.`}
          </p>
        </div>
        <Button onClick={onReplace} className="w-full">
          Create a new invoice
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-center space-y-1">
        <p className="text-2xl font-bold text-[var(--color-text-primary)]">
          {formatIdr(topup.totalIdr)}
        </p>
        <p className="text-xs text-[var(--color-text-muted)]">
          for {formatUsd(topup.usdAmount)} of credit · invoice {topup.id}
        </p>
      </div>

      <div className="flex justify-center">
        {qrDataUrl ? (
          <img
            src={qrDataUrl}
            alt="QRIS payment code"
            className="w-[240px] h-[240px] rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-white"
          />
        ) : (
          <div className="w-[240px] h-[240px] flex items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-border-light)]">
            <Loader2 className="w-6 h-6 animate-spin text-[var(--color-text-muted)]" />
          </div>
        )}
      </div>

      <p className="text-xs text-center text-[var(--color-text-secondary)]">
        Scan with any bank or e-wallet app. QRIS is exact-amount — pay
        {" "}
        {formatIdr(topup.totalIdr)}.
        {countdown && (
          <>
            <br />
            <span className="text-[var(--color-text-muted)]">
              Expires in {countdown}
            </span>
          </>
        )}
      </p>

      <Button
        variant="outline"
        onClick={checkNow}
        disabled={checking}
        className="w-full gap-2"
      >
        {checking ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <RefreshCw className="w-4 h-4" />
        )}
        I have paid
      </Button>

      <p className="text-[11px] text-center text-[var(--color-text-muted)]">
        You can close this window. A payment that lands later is still credited,
        and the balance will be right the next time you open the app.
      </p>
    </div>
  );
}

function Row({
  label,
  value,
  strong,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[var(--color-text-secondary)]">{label}</span>
      <span
        className={
          strong
            ? "font-semibold text-[var(--color-text-primary)]"
            : "text-[var(--color-text-primary)]"
        }
      >
        {value}
      </span>
    </div>
  );
}
