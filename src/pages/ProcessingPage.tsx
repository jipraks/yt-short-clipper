import { useEffect, useRef, useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Loader2, Circle, AlertCircle, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useProcessingStore, type Step } from "@/stores/processingStore";
import { useSessionStore } from "@/stores/sessionStore";
import { findHighlights } from "@/hooks/highlights";
import { formatLogTime } from "@/utils/format";
import { toast } from "sonner";

function levelForMessage(message: string): "info" | "warn" | "error" | "success" {
  const m = message.toLowerCase();
  if (m.startsWith("ok ") || m.includes("found ") || m.includes("complete")) return "success";
  if (m.startsWith("skip") || m.includes("warn")) return "warn";
  if (m.includes("error") || m.includes("failed")) return "error";
  return "info";
}

function StepIcon({ status }: { status: Step["status"] }) {
  switch (status) {
    case "done":
      return <CheckCircle2 className="w-5 h-5 text-[var(--color-success)]" />;
    case "running":
      return <Loader2 className="w-5 h-5 text-[var(--color-accent)] animate-spin" />;
    case "error":
      return <AlertCircle className="w-5 h-5 text-[var(--color-error)]" />;
    default:
      return <Circle className="w-5 h-5 text-[var(--color-text-muted)]" />;
  }
}

export function ProcessingPage() {
  const navigate = useNavigate();
  const { isProcessing, steps, logLines, error, request, updateStep, appendLog, setError, finish } =
    useProcessingStore();
  const { setSession } = useSessionStore();
  const logEndRef = useRef<HTMLDivElement>(null);
  const startedRef = useRef(false);
  const [copied, setCopied] = useState(false);

  const copyLog = useCallback(async () => {
    const text = logLines
      .map((l) => `[${formatLogTime(l.ts)}] ${l.level.toUpperCase()}: ${l.message}`)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success("Log copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy log");
    }
  }, [logLines]);

  const run = useCallback(async () => {
    if (!request) {
      navigate("/");
      return;
    }

    updateStep(0, "running");
    appendLog({ level: "info", message: "Starting...", ts: Date.now() });

    try {
      const session = await findHighlights({
        url: request.url,
        numClips: request.numClips,
        subtitleLanguage: request.subtitleLanguage,
        ai: request.ai,
        userDirection: request.userDirection,
        outputLanguage: request.outputLanguage,
        onLog: (message) => {
          appendLog({ level: levelForMessage(message), message, ts: Date.now() });
          const m = message.toLowerCase();
          if (m.includes("finding highlights")) {
            updateStep(0, "done");
            updateStep(1, "running");
          }
        },
      });

      finish();
      setSession(session);
      appendLog({
        level: "success",
        message: `Found ${session.highlights.length} highlights`,
        ts: Date.now(),
      });
      setTimeout(() => navigate("/highlights"), 600);
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : typeof err === "string" ? err : JSON.stringify(err);
      console.error("find_highlights failed", err);
      setError(detail);
      appendLog({ level: "error", message: detail, ts: Date.now() });
    }
  }, [request, navigate, updateStep, appendLog, finish, setSession, setError]);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    run();
  }, [run]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logLines]);

  return (
    <div className="space-y-5">
      <Button
        variant="ghost"
        onClick={() => navigate("/")}
        className="gap-2 text-[var(--color-text-secondary)]"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </Button>

      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
          {error
            ? "Something went wrong"
            : isProcessing
              ? "Finding highlights..."
              : "Highlights ready"}
        </h2>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          {error
            ? "Review the log below and try again."
            : "Downloading subtitle and analyzing the transcript with AI."}
        </p>
      </div>

      {/* Steps */}
      <Card className="p-4">
        <div className="space-y-2.5">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <StepIcon status={step.status} />
              <span
                className={`text-sm ${
                  step.status === "running"
                    ? "text-[var(--color-accent)] font-medium"
                    : step.status === "done"
                      ? "text-[var(--color-text-primary)]"
                      : step.status === "error"
                        ? "text-[var(--color-error)]"
                        : "text-[var(--color-text-muted)]"
                }`}
              >
                {step.label}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* Log console */}
      <Card className="p-0 overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border-light)] bg-[var(--color-bg-sidebar)]">
          <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wide">
            Log Output
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={copyLog}
            disabled={logLines.length === 0}
            className="h-7 gap-1.5 text-xs"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                Copy
              </>
            )}
          </Button>
        </div>
        <div className="h-[260px] overflow-y-auto p-3 font-mono text-xs space-y-1 bg-[var(--color-bg-primary)]">
          {logLines.map((line, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-[var(--color-text-muted)] shrink-0">
                [{formatLogTime(line.ts)}]
              </span>
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
          <div ref={logEndRef} />
        </div>
      </Card>

      {error && (
        <Button onClick={() => navigate("/")} variant="outline" className="w-full">
          Back to Create
        </Button>
      )}
    </div>
  );
}
