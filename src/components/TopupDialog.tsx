import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import QRCode from "qrcode";
import { AlertTriangle, Check, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
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
import { cn } from "@/lib/utils";
import { countdownTo, formatIdr, formatUsd } from "@/utils/format";

/** How often the open dialog asks the server. The API throttles at 4s anyway. */
const POLL_MS = 4000;

const QUICK_AMOUNTS = [5, 10, 25, 50];

interface TopupDialogProps {
  onClose: () => void;
}

export function TopupDialog({ onClose }: TopupDialogProps) {
  const { t } = useTranslation();
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
    <Modal
      title={t("billing.topup.title")}
      closeLabel={t("billing.topup.close")}
      onClose={onClose}
      className="max-h-[90vh] overflow-y-auto"
    >
      {(close) =>
        topup ? (
          <InvoicePanel topup={topup} onReplace={() => setTopup(null)} onDone={close} />
        ) : (
          <AmountPanel onCreated={setTopup} />
        )
      }
    </Modal>
  );
}

/** 0 choose amount, 1 scan, 2 paid. A step before `current` shows as done. */
function Steps({ current }: { current: 0 | 1 | 2 }) {
  const { t } = useTranslation();
  const labels = [t("billing.topup.steps.amount"), t("billing.topup.steps.pay"), t("billing.topup.steps.paid")];
  const allDone = current === 2;

  return (
    <ol aria-label={t("billing.topup.steps.label")} className="mt-4 flex items-center gap-2 text-xs">
      {labels.map((label, i) => {
        const done = i < current || allDone;
        const active = i === current;
        return (
          <li key={label} aria-current={active ? "step" : undefined} className="flex min-w-0 items-center gap-2">
            {i > 0 && <span aria-hidden className="h-px w-4 shrink-0 bg-[var(--color-border)]" />}
            <span
              aria-hidden
              className={cn(
                "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold",
                done
                  ? "border-[var(--color-success)] text-[var(--color-success)]"
                  : active
                    ? "border-[var(--color-accent)] text-[var(--color-accent)]"
                    : "border-[var(--color-border)] text-[var(--color-text-muted)]",
              )}
            >
              {done ? <Check className="h-3 w-3" /> : i + 1}
            </span>
            <span
              className={cn(
                "truncate",
                active ? "font-semibold text-[var(--color-text-primary)]" : "text-[var(--color-text-muted)]",
              )}
            >
              {label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function AmountPanel({ onCreated }: { onCreated: (topup: Topup) => void }) {
  const { t } = useTranslation();
  const [rate, setRate] = useState<FeeRate | null>(null);
  const [rateError, setRateError] = useState<string | null>(null);
  const [amount, setAmount] = useState(10);
  const [creating, setCreating] = useState(false);

  const loadRate = useCallback(() => {
    setRateError(null);
    fetchFeeRate()
      .then((value) => {
        setRate(value);
        setAmount((current) => Math.min(Math.max(current, value.minTopupUsd), value.maxTopupUsd));
      })
      .catch((err) => setRateError(errorMessage(err)));
  }, []);

  useEffect(() => {
    loadRate();
  }, [loadRate]);

  // Quoted locally so dragging the amount does not cost a request per
  // keystroke. The invoice the server issues is the one that counts.
  const idrAmount = rate ? Math.round(amount * rate.usdIdrRate) : null;
  const feeIdr = rate && idrAmount !== null ? Math.round((idrAmount * rate.platformFeePercent) / 100) : null;
  const totalIdr = idrAmount !== null && feeIdr !== null ? idrAmount + feeIdr : null;

  const withinRange = !rate || (amount >= rate.minTopupUsd && amount <= rate.maxTopupUsd);

  const create = async () => {
    setCreating(true);
    try {
      onCreated(await createTopup(amount));
    } catch (err) {
      toast.error(t("billing.topup.amount.createFailed", { reason: errorMessage(err) }));
    } finally {
      setCreating(false);
    }
  };

  const presets = QUICK_AMOUNTS.filter((value) => !rate || (value >= rate.minTopupUsd && value <= rate.maxTopupUsd));

  return (
    <>
      <Steps current={0} />
      <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-secondary)]">{t("billing.topup.amount.body")}</p>

      <label htmlFor="topup-amount" className="mt-5 mb-1.5 block text-xs font-medium text-[var(--color-text-muted)]">
        {t("billing.topup.amount.label")}
      </label>
      <Input
        id="topup-amount"
        type="number"
        value={amount}
        min={rate?.minTopupUsd ?? 1}
        max={rate?.maxTopupUsd ?? 1000}
        step={1}
        aria-invalid={!withinRange}
        aria-describedby={!withinRange ? "topup-amount-error" : undefined}
        onChange={(e) => setAmount(Math.floor(Number(e.target.value) || 0))}
      />
      <div role="group" aria-label={t("billing.topup.amount.presets")} className="mt-2 flex gap-2">
        {presets.map((value) => {
          const selected = amount === value;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={selected}
              onClick={() => setAmount(value)}
              className={cn(
                "h-9 flex-1 rounded-[var(--radius-sm)] border text-sm font-medium cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]",
                selected
                  ? "border-[var(--color-accent)] bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
                  : "border-[var(--color-border)] bg-[var(--color-bg-primary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]",
              )}
            >
              ${value}
            </button>
          );
        })}
      </div>
      {rate && !withinRange && (
        <p id="topup-amount-error" className="mt-2 text-xs text-[var(--color-error)]">
          {t("billing.topup.amount.outOfRange", {
            min: formatUsd(rate.minTopupUsd),
            max: formatUsd(rate.maxTopupUsd),
          })}
        </p>
      )}

      <div className="mt-5 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4 text-sm">
        {rate ? (
          <>
            <div className="flex items-end justify-between gap-3">
              <div>
                <p className="text-xs text-[var(--color-text-muted)]">{t("billing.topup.amount.youPay")}</p>
                <p className="mt-0.5 text-2xl font-bold tabular-nums text-[var(--color-text-primary)]">
                  {formatIdr(totalIdr ?? 0)}
                </p>
              </div>
              <p className="pb-1 text-sm font-semibold tabular-nums text-[var(--color-text-secondary)]">
                {formatUsd(amount)}
              </p>
            </div>
            <div className="mt-3 space-y-1.5 border-t border-[var(--color-border)] pt-3">
              <Row label={t("billing.topup.amount.credit", { usd: formatUsd(amount) })} value={formatIdr(idrAmount ?? 0)} />
              <Row
                label={t("billing.topup.amount.fee", { percent: rate.platformFeePercent })}
                value={formatIdr(feeIdr ?? 0)}
              />
              <Row label={t("billing.topup.amount.total")} value={formatIdr(totalIdr ?? 0)} strong />
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--color-text-muted)]">
              {t("billing.topup.amount.rate", { idr: formatIdr(rate.usdIdrRate) })}
            </p>
          </>
        ) : rateError ? (
          <div role="alert" className="flex items-start gap-2.5">
            <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-error)]" />
            <div className="min-w-0">
              <p className="text-[var(--color-text-secondary)] break-words">
                {t("billing.topup.amount.rateFailed", { reason: rateError })}
              </p>
              <button
                type="button"
                onClick={loadRate}
                className="mt-1 inline-flex h-9 items-center rounded-[var(--radius-sm)] text-sm font-medium text-[var(--color-accent)] hover:underline cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
              >
                {t("billing.topup.amount.retryRate")}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-[var(--color-text-muted)]">
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
            {t("billing.topup.amount.loadingRate")}
          </div>
        )}
      </div>

      <Button onClick={create} disabled={creating || !rate || !withinRange} className="mt-6 h-11 w-full gap-2">
        {creating && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
        {creating ? t("billing.topup.amount.creating") : t("billing.topup.amount.create")}
      </Button>
    </>
  );
}

function InvoicePanel({
  topup: initial,
  onReplace,
  onDone,
}: {
  topup: Topup;
  onReplace: () => void;
  onDone: () => void;
}) {
  const { t } = useTranslation();
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
        if (force) toast.error(t("billing.topup.pay.checkFailed", { reason: errorMessage(err) }));
        return null;
      }
    },
    [topup.id, refreshAccount, t],
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
        toast.info(t("billing.topup.pay.notYet"));
      }
    } finally {
      setChecking(false);
    }
  };

  const usd = formatUsd(topup.usdAmount);
  const idr = formatIdr(topup.totalIdr);

  if (topup.status === "paid") {
    return (
      <>
        <Steps current={2} />
        <div role="status" className="mt-6 text-center">
          <CheckCircle2 aria-hidden className="mx-auto h-12 w-12 text-[var(--color-success)]" />
          <p className="mt-3 text-base font-semibold text-[var(--color-text-primary)]">
            {t("billing.topup.paid.title", { usd })}
          </p>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("billing.topup.paid.body")}</p>
          <p className="mt-2 font-mono text-xs text-[var(--color-text-muted)]">
            {t("billing.topup.paid.invoice", { id: topup.id })}
          </p>
        </div>
        <Button onClick={onDone} className="mt-6 h-11 w-full">
          {t("billing.topup.paid.done")}
        </Button>
      </>
    );
  }

  if (settled) {
    const [title, body] =
      topup.status === "expired"
        ? [t("billing.topup.ended.expiredTitle"), t("billing.topup.ended.expiredBody")]
        : topup.status === "cancelled"
          ? [t("billing.topup.ended.cancelledTitle"), t("billing.topup.ended.cancelledBody")]
          : [t("billing.topup.ended.failedTitle"), t("billing.topup.ended.failedBody")];
    return (
      <>
        <Steps current={1} />
        <div
          role="alert"
          className="mt-5 flex items-start gap-3 rounded-[var(--radius)] border border-[var(--color-warning)]/30 bg-[var(--color-warning-bg)] p-4"
        >
          <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-warning)]" />
          <div>
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">{title}</p>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{body}</p>
            <p className="mt-2 font-mono text-xs text-[var(--color-text-muted)]">
              {t("billing.topup.pay.invoice", { id: topup.id })}
            </p>
          </div>
        </div>
        <Button onClick={onReplace} className="mt-6 h-11 w-full">
          {t("billing.topup.ended.retry")}
        </Button>
      </>
    );
  }

  return (
    <>
      <Steps current={1} />

      <div className="mt-5 text-center">
        <p className="text-2xl font-bold tabular-nums text-[var(--color-text-primary)]">{idr}</p>
        <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">
          {t("billing.topup.pay.forCredit", { usd })}
          <span aria-hidden> · </span>
          <span className="font-mono">{t("billing.topup.pay.invoice", { id: topup.id })}</span>
        </p>
      </div>

      <div className="mt-4 flex justify-center">
        {qrDataUrl ? (
          <img
            src={qrDataUrl}
            alt={t("billing.topup.pay.qrAlt", { idr })}
            className="h-[240px] w-[240px] rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-white"
          />
        ) : (
          <div
            role="status"
            aria-label={t("billing.topup.pay.qrLoading")}
            className="flex h-[240px] w-[240px] items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-border)]"
          >
            <Loader2 aria-hidden className="h-6 w-6 animate-spin text-[var(--color-text-muted)]" />
          </div>
        )}
      </div>

      <div role="status" className="mt-4 flex items-center justify-center gap-2 text-sm font-medium text-[var(--color-text-primary)]">
        <Loader2 aria-hidden className="h-4 w-4 animate-spin text-[var(--color-text-muted)]" />
        {t("billing.topup.pay.waiting")}
      </div>
      <p className="mt-1 text-center text-xs tabular-nums text-[var(--color-text-muted)]">
        {countdown
          ? t("billing.topup.pay.expiresIn", { time: countdown })
          : topup.expiresAt
            ? t("billing.topup.pay.expiredChecking")
            : null}
      </p>

      <p className="mt-4 text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {t("billing.topup.pay.howTo", { idr })}
      </p>
      <p className="mt-1.5 text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {t("billing.topup.pay.autoUpdate")}
      </p>

      <Button onClick={checkNow} disabled={checking} className="mt-6 h-11 w-full gap-2">
        {checking && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
        {checking ? t("billing.topup.pay.checking") : t("billing.topup.pay.checkNow")}
      </Button>

      <p className="mt-3 text-xs leading-relaxed text-[var(--color-text-muted)]">{t("billing.topup.pay.closeNote")}</p>
    </>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[var(--color-text-secondary)]">{label}</span>
      <span
        className={cn(
          "tabular-nums text-[var(--color-text-primary)]",
          strong && "font-semibold",
        )}
      >
        {value}
      </span>
    </div>
  );
}
