import { useEffect, useRef, useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useProcessingStore, type Step, type StepId } from "@/stores/processingStore";
import { useSessionStore } from "@/stores/sessionStore";
import { findHighlights } from "@/hooks/highlights";
import { TechnicalLog, clock, levelForMessage, shortError } from "@/components/process/TechnicalLog";
import { extractVideoId, fetchVideoInfo, getThumbnailUrl, type VideoInfo } from "@/utils/youtube";
import { cn } from "@/lib/utils";

export function ProcessingPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { isProcessing, steps, logLines, error, request, start, updateStep, appendLog, setError, finish } =
    useProcessingStore();
  const { setSession } = useSessionStore();
  const startedRef = useRef(false);
  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);
  const [showLog, setShowLog] = useState(false);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);

  const videoId = request ? extractVideoId(request.url) : null;

  useEffect(() => {
    if (!videoId) return;
    const controller = new AbortController();
    fetchVideoInfo(videoId, controller.signal).then((info) => {
      if (!controller.signal.aborted) setVideoInfo(info);
    });
    return () => controller.abort();
  }, [videoId]);

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
          // The sidecar announces each phase in its log; move the stepper on those.
          const m = message.toLowerCase();
          if (m.includes("finding highlights")) {
            updateStep(0, "done");
            updateStep(1, "running");
          } else if (m.includes("extracting transcript text")) {
            updateStep(1, "done");
            updateStep(2, "running");
          }
        },
      });

      finish();
      setSession(session);
      appendLog({ level: "success", message: `Found ${session.highlights.length} highlights`, ts: Date.now() });
      setTimeout(() => navigate("/highlights"), 700);
    } catch (err) {
      const detail = err instanceof Error ? err.message : typeof err === "string" ? err : JSON.stringify(err);
      console.error("find_highlights failed", err);
      setError(detail);
      setShowLog(true);
      appendLog({ level: "error", message: detail, ts: Date.now() });
    }
  }, [request, navigate, updateStep, appendLog, finish, setSession, setError]);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    void run();
  }, [run]);

  // Running clock, stopped once the run ends either way.
  useEffect(() => {
    if (!isProcessing) return;
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [isProcessing, startedAt]);

  const retry = () => {
    if (!request) return;
    start(request);
    setStartedAt(Date.now());
    setElapsed(0);
    setShowLog(false);
    // start() resets the store; run again on the next tick so it sees the reset.
    setTimeout(() => void run(), 0);
  };

  const current = steps.findIndex((s) => s.status === "running" || s.status === "error");
  const focusStep: Step | undefined = steps[current >= 0 ? current : steps.length - 1];
  const done = !isProcessing && !error;
  const lastLine = logLines.length ? logLines[logLines.length - 1].message : "";

  const stepBody = (id: StepId) =>
    id === "ai"
      ? `${t("processing.steps.ai.body", { count: request?.numClips ?? 0 })}${request?.userDirection ? ` ${t("processing.steps.ai.direction")}` : ""}`
      : t(`processing.steps.${id}.body`);

  return (
    <div className="mx-auto max-w-[760px] py-4">
      {/* Which video this is about */}
      {videoId && (
        <div className="flex items-center gap-4">
          <img
            src={getThumbnailUrl(videoId, "mq")}
            alt=""
            className="aspect-video w-28 shrink-0 rounded-[var(--radius-sm)] border border-[var(--color-border)] object-cover"
          />
          <div className="min-w-0">
            <p className="text-sm text-[var(--color-text-muted)]">
              {error ? t("processing.errorTitle") : done ? t("processing.doneTitle") : t("processing.title")}
            </p>
            <p className="mt-0.5 line-clamp-2 text-lg font-semibold text-[var(--color-text-primary)] leading-snug">
              {videoInfo?.title ?? request?.url}
            </p>
          </div>
        </div>
      )}

      {/* The steps, left to right */}
      <ol className="mt-8 grid grid-cols-3 gap-2">
        {steps.map((step, i) => (
          <StepPill key={step.id} step={step} n={i + 1} last={i === steps.length - 1} label={t(`processing.steps.${step.id}.title`)} />
        ))}
      </ol>

      {/* What is happening right now */}
      <section
        aria-live="polite"
        className={cn(
          "mt-6 rounded-[var(--radius-lg)] border p-5",
          error ? "border-[var(--color-error)]/40 bg-[var(--color-error-bg)]" : "border-[var(--color-border)] bg-[var(--color-bg-primary)]",
        )}
      >
        {error ? (
          <>
            <p className="text-base font-semibold text-[var(--color-text-primary)]">{t("processing.errorTitle")}</p>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("processing.errorBody")}</p>
            <p className="mt-3 whitespace-pre-line break-words text-sm text-[var(--color-error)]">{shortError(error)}</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button onClick={retry} className="h-11 px-5">
                {t("processing.retry")}
              </Button>
              <Button variant="outline" onClick={() => navigate("/")} className="h-11 px-5">
                {t("processing.backToCreate")}
              </Button>
            </div>
          </>
        ) : focusStep ? (
          <>
            <div className="flex items-baseline justify-between gap-4">
              <p className="text-xs font-medium text-[var(--color-text-muted)]">
                {t("processing.stepOf", { n: steps.indexOf(focusStep) + 1, total: steps.length })}
              </p>
              <p className="text-xs tabular-nums text-[var(--color-text-muted)]">
                {t("processing.elapsed", { time: clock(elapsed) })}
              </p>
            </div>
            <p className="mt-1 text-xl font-bold text-[var(--color-text-primary)]">
              {done ? t("processing.doneTitle") : t(`processing.steps.${focusStep.id}.title`)}
            </p>
            {!done && (
              <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{stepBody(focusStep.id)}</p>
            )}
            {!done && lastLine && (
              <p className="mt-4 truncate text-xs text-[var(--color-text-muted)]">
                {t("processing.lastActivity")}: <span className="font-mono">{lastLine}</span>
              </p>
            )}
            {isProcessing && <p className="mt-4 text-xs text-[var(--color-text-muted)]">{t("processing.keepOpen")}</p>}
          </>
        ) : null}
      </section>

      <TechnicalLog lines={logLines} open={showLog} onToggle={() => setShowLog((v) => !v)} />
    </div>
  );
}

/** One step in the row: number or state, title, and a line to the next. */
function StepPill({ step, n, last, label }: { step: Step; n: number; last: boolean; label: string }) {
  const active = step.status === "running";
  return (
    <li className="relative flex flex-col items-center text-center" aria-current={active ? "step" : undefined}>
      {!last && (
        <span
          aria-hidden
          className={cn(
            "absolute left-[calc(50%+22px)] right-[calc(-50%+22px)] top-[17px] h-0.5 rounded-full",
            step.status === "done" ? "bg-[var(--color-success)]" : "bg-[var(--color-border)]",
          )}
        />
      )}
      <span
        className={cn(
          "relative flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-bold tabular-nums",
          step.status === "done" && "border-[var(--color-success)] bg-[var(--color-success)] text-[var(--color-bg-secondary)]",
          step.status === "running" && "border-[var(--color-accent)] text-[var(--color-accent)]",
          step.status === "error" && "border-[var(--color-error)] bg-[var(--color-error)] text-[var(--color-bg-secondary)]",
          step.status === "pending" && "border-[var(--color-border)] text-[var(--color-text-muted)]",
        )}
      >
        {step.status === "done" ? (
          <Check aria-hidden className="h-4 w-4" strokeWidth={3} />
        ) : step.status === "error" ? (
          <X aria-hidden className="h-4 w-4" strokeWidth={3} />
        ) : (
          n
        )}
        {active && (
          // A ring that turns while this step runs; still for reduced motion.
          <span
            aria-hidden
            className="absolute -inset-1 rounded-full border-2 border-transparent border-t-[var(--color-accent)] motion-safe:animate-spin [animation-duration:1.2s]"
          />
        )}
      </span>
      <span
        className={cn(
          "mt-2 text-sm",
          active ? "font-semibold text-[var(--color-text-primary)]" : step.status === "done" ? "text-[var(--color-text-secondary)]" : step.status === "error" ? "text-[var(--color-error)]" : "text-[var(--color-text-muted)]",
        )}
      >
        {label}
      </span>
    </li>
  );
}
