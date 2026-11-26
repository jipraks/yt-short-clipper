import { cn } from "@/lib/utils";

/**
 * The Cuplik wordmark, after the owner's sketch: CUP in the brand red, LIK in
 * white, uppercase. Set as live text in Plus Jakarta Sans so it matches the UI
 * and stays sharp at any size; the visible letters are hidden from screen
 * readers in favour of the plain name.
 */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span role="img" aria-label="Cuplik" className={cn("inline-flex font-semibold uppercase leading-none tracking-[0.04em]", className)}>
      <span aria-hidden className="text-[var(--color-accent)]">
        Cup
      </span>
      <span aria-hidden className="text-[var(--color-text-primary)]">
        lik
      </span>
    </span>
  );
}
