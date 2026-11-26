import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, ChevronDown, Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { formatLogTime } from "@/utils/format";
import { cn } from "@/lib/utils";

export interface LogLine {
  level: string;
  message: string;
  ts: number;
}

export function levelForMessage(message: string): "info" | "warn" | "error" | "success" {
  const m = message.toLowerCase();
  if (m.startsWith("ok ") || m.includes("found ") || m.includes("complete")) return "success";
  if (m.startsWith("skip") || m.includes("warn")) return "warn";
  if (m.includes("error") || m.includes("failed")) return "error";
  return "info";
}

/** "1:05" or "12:40", for the running clock. */
export function clock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** The sentence to show for a failure: the sidecar's message without its stderr dump. */
export function shortError(detail: string): string {
  return detail.split("\n\nstderr:")[0].replace(/^Sidecar error: /, "").trim();
}

/** The sidecar's own log, out of the way until someone needs it. */
export function TechnicalLog({
  lines,
  open,
  onToggle,
}: {
  lines: LogLine[];
  open: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Follow the newest line inside the box only; scrolling the page would pull
  // whatever the user is reading out of view.
  useEffect(() => {
    const box = boxRef.current;
    if (open && box) box.scrollTop = box.scrollHeight;
  }, [lines, open]);

  const copy = async () => {
    const text = lines.map((l) => `[${formatLogTime(l.ts)}] ${l.level.toUpperCase()}: ${l.message}`).join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success(t("processing.log.copied"));
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("processing.log.copyFailed"));
    }
  };

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          aria-expanded={open}
          onClick={onToggle}
          className="inline-flex min-h-11 items-center gap-1.5 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
        >
          <ChevronDown aria-hidden className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
          {open ? t("processing.log.hide") : t("processing.log.show")}
        </button>
        {open && (
          <Button variant="ghost" size="sm" onClick={copy} disabled={lines.length === 0} className="h-9 gap-1.5">
            {copied ? <Check aria-hidden className="h-3.5 w-3.5 text-[var(--color-success)]" /> : <Copy aria-hidden className="h-3.5 w-3.5" />}
            {copied ? t("processing.log.copied") : t("processing.log.copy")}
          </Button>
        )}
      </div>
      {open && (
        <div ref={boxRef} className="mt-2 max-h-[260px] overflow-y-auto rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-3 font-mono text-xs space-y-1">
          {lines.map((line, i) => (
            <div key={i} className="flex gap-2">
              <span className="shrink-0 text-[var(--color-text-muted)]">[{formatLogTime(line.ts)}]</span>
              <span
                className={
                  line.level === "error"
                    ? "text-[var(--color-error)]"
                    : line.level === "success"
                      ? "text-[var(--color-success)]"
                      : line.level === "warn"
                        ? "text-[var(--color-warning)]"
                        : "text-[var(--color-text-secondary)]"
                }
              >
                {line.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
