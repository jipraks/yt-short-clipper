import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

/** Work that finishes this fast never shows the modal, so it cannot flicker. */
const SHOW_AFTER_MS = 300;
/** Matches the exit animation below. */
const EXIT_MS = 160;

type Phase = "hidden" | "entering" | "leaving";

/**
 * A modal that holds the screen while something the user just started is
 * running, so a wait is never mistaken for nothing happening. It always has a
 * way out: Cancel, or Escape.
 *
 * It waits a moment before appearing, fades and lifts in, and fades out when
 * the work ends. Focus goes to the panel rather than the button, so no focus
 * ring lights up the moment it opens. The spinner says "still working"; it and
 * every transition stop for anyone who asked the OS to reduce motion.
 */
export function BlockingProgress({
  open,
  title,
  body,
  elapsedLabel,
  cancelLabel,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: string;
  elapsedLabel: (seconds: number) => string;
  cancelLabel: string;
  onCancel: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("hidden");

  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => setPhase("entering"), SHOW_AFTER_MS);
      return () => clearTimeout(timer);
    }
    // Closing: play the exit only if it was on screen.
    setPhase((current) => (current === "hidden" ? "hidden" : "leaving"));
    const timer = setTimeout(() => setPhase("hidden"), EXIT_MS);
    return () => clearTimeout(timer);
  }, [open]);

  if (phase === "hidden") return null;
  return (
    <Panel
      leaving={phase === "leaving"}
      title={title}
      body={body}
      elapsedLabel={elapsedLabel}
      cancelLabel={cancelLabel}
      onCancel={onCancel}
    />
  );
}

function Panel({
  leaving,
  title,
  body,
  elapsedLabel,
  cancelLabel,
  onCancel,
}: {
  leaving: boolean;
  title: string;
  body: string;
  elapsedLabel: (seconds: number) => string;
  cancelLabel: string;
  onCancel: () => void;
}) {
  const [seconds, setSeconds] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panelRef.current?.focus();
    const started = Date.now();
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (leaving) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [leaving, onCancel]);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 ${
        leaving
          ? "pointer-events-none motion-safe:animate-[cuplik-overlay-out_160ms_ease-in_forwards]"
          : "motion-safe:animate-[cuplik-overlay-in_200ms_ease-out]"
      }`}
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="blocking-progress-title"
        aria-describedby="blocking-progress-body"
        className={`w-full max-w-sm rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-card)] p-6 text-center shadow-[var(--shadow-lg)] outline-none ${
          leaving
            ? "motion-safe:animate-[cuplik-panel-out_160ms_ease-in_forwards]"
            : "motion-safe:animate-[cuplik-panel-in_250ms_cubic-bezier(0.16,1,0.3,1)]"
        }`}
      >
        <svg aria-hidden viewBox="0 0 48 48" className="mx-auto h-14 w-14 motion-safe:animate-spin [animation-duration:1.1s]">
          <circle cx="24" cy="24" r="20" fill="none" stroke="var(--color-border)" strokeWidth="4" />
          <circle
            cx="24"
            cy="24"
            r="20"
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray="38 126"
          />
        </svg>
        <h2 id="blocking-progress-title" className="mt-5 text-lg font-bold text-[var(--color-text-primary)]">
          {title}
        </h2>
        <p id="blocking-progress-body" className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">
          {body}
        </p>
        <p className="mt-3 text-sm tabular-nums text-[var(--color-text-muted)]">{elapsedLabel(seconds)}</p>
        <Button variant="outline" onClick={onCancel} disabled={leaving} className="mt-5 h-11 w-full">
          {cancelLabel}
        </Button>
      </div>
    </div>
  );
}
