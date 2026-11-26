import { useCallback, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/** Matches cuplik-panel-out. */
const EXIT_MS = 160;

/**
 * A centred dialog with Cuplik's enter and exit motion. It closes on Escape,
 * on the X, and on a click outside, always through the exit animation, then
 * calls onClose. Focus lands on the panel, not a button, so nothing lights up
 * on open. Children get `close` so their own buttons leave the same way.
 */
export function Modal({
  title,
  icon,
  closeLabel,
  onClose,
  className,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  closeLabel: string;
  onClose: () => void;
  className?: string;
  children: (close: () => void) => React.ReactNode;
}) {
  const [leaving, setLeaving] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useRef(`modal-${Math.random().toString(36).slice(2)}`).current;

  const close = useCallback(() => {
    setLeaving((was) => {
      if (!was) setTimeout(onClose, EXIT_MS);
      return true;
    });
  }, [onClose]);

  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4",
        leaving
          ? "pointer-events-none motion-safe:animate-[cuplik-overlay-out_160ms_ease-in_forwards]"
          : "motion-safe:animate-[cuplik-overlay-in_200ms_ease-out]",
      )}
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cn(
          "w-full max-w-md rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6 shadow-[var(--shadow-lg)] outline-none",
          leaving
            ? "motion-safe:animate-[cuplik-panel-out_160ms_ease-in_forwards]"
            : "motion-safe:animate-[cuplik-panel-in_250ms_cubic-bezier(0.16,1,0.3,1)]",
          className,
        )}
      >
        <div className="flex items-start justify-between gap-4">
          <h2 id={titleId} className="flex items-center gap-2.5 text-lg font-bold text-[var(--color-text-primary)]">
            {icon}
            {title}
          </h2>
          <button
            type="button"
            onClick={close}
            aria-label={closeLabel}
            className="-mr-2 -mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            <X aria-hidden className="h-5 w-5" />
          </button>
        </div>
        {children(close)}
      </div>
    </div>
  );
}
