import { useEffect, useRef, useCallback, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { processClips, type ProcessOptions } from "@/hooks/processClips";
import { trackClipRendered, type ReframeFormat } from "@/hooks/analytics";
import { useConfigStore } from "@/stores/configStore";
import { inappSupported, useAccountStore } from "@/stores/accountStore";
import { aiBlocker, buildAIRequest, type AIBlocker } from "@/hooks/aiRuntime";
import { isOutOfBalance } from "@/hooks/account";
import { TopupDialog } from "@/components/TopupDialog";
import { TechnicalLog, clock, levelForMessage, shortError, type LogLine } from "@/components/process/TechnicalLog";
import { extractVideoId, fetchVideoInfo, getThumbnailUrl, type VideoInfo } from "@/utils/youtube";
import { cn } from "@/lib/utils";

interface ClipProcessingState {
  url: string;
  highlights: unknown[];
  sessionDir: string;
  options: ProcessOptions;
}

/** What one clip goes through, in order. Stages the options turn off are left out. */
type Stage = "download" | "reframe" | "hook" | "captions" | "overlay" | "save";

interface ClipState {
  status: "waiting" | "running" | "done" | "skipped" | "error";
  stage: Stage;
}

type Failure =
  | { kind: "blocker"; blocker: AIBlocker }
  | { kind: "balance" }
  | { kind: "error"; detail: string };

function stagesFor(options: ProcessOptions): Stage[] {
  const stages: Stage[] = ["download"];
  if (options.reframeMode !== "original") stages.push("reframe");
  if (options.addHook) stages.push("hook");
  if (options.addCaptions) stages.push("captions");
  if (options.addWatermark || options.addCreditWatermark) stages.push("overlay");
  stages.push("save");
  return stages;
}

/**
 * Reads one sidecar log line and says which clip it is about and what that
 * clip moves on to. The worker prefixes per-clip lines with "[i/total]".
 */
function transition(message: string): { index: number; next: Stage | "done" | "skipped" } | null {
  const m = message.toLowerCase();
  const start = /^processing clip (\d+)\/\d+/.exec(m);
  if (start) return { index: Number(start[1]) - 1, next: "download" };
  const tagged = /^\[(\d+)\/\d+\]/.exec(m);
  if (!tagged) return null;
  const index = Number(tagged[1]) - 1;
  if (m.includes("already processed")) return { index, next: "skipped" };
  if (m.includes("section downloaded")) return { index, next: "reframe" };
  if (m.includes("portrait conversion")) return { index, next: "hook" };
  if (m.includes("hook generation") || m.includes("no hook text")) return { index, next: "captions" };
  if (m.includes("caption") || m.includes("no subtitle words")) return { index, next: "overlay" };
  if (m.includes("watermark overlay")) return { index, next: "save" };
  if (m.includes("clip saved")) return { index, next: "done" };
  return null;
}

/** A clip's next stage, stepping over the ones this run does not do. */
function settle(stage: Stage, stages: Stage[]): Stage {
  const order: Stage[] = ["download", "reframe", "hook", "captions", "overlay", "save"];
  for (let i = order.indexOf(stage); i < order.length; i++) {
    if (stages.includes(order[i])) return order[i];
  }
  return "save";
}

export function ProcessingClipsPage() {
  const location = useLocation();
  const state = location.state as ClipProcessingState | undefined;
  if (!state) return <Navigate to="/" replace />;
  return <RenderRun state={state} />;
}

function RenderRun({ state }: { state: ClipProcessingState }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { config } = useConfigStore();
  const { activated, account, appInfo, refresh: refreshAccount } = useAccountStore();
  const { url, highlights, sessionDir, options } = state;
  const stages = stagesFor(options);
  // The session folder's name is its id; the Clips page filters on it.
  const clipsUrl = `/clips?session=${encodeURIComponent(sessionDir.split(/[\\/]/).filter(Boolean).pop() ?? "")}`;
  const total = highlights.length;

  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [clips, setClips] = useState<ClipState[]>(() => highlights.map(() => ({ status: "waiting", stage: "download" })));
  const [failure, setFailure] = useState<Failure | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [running, setRunning] = useState(true);
  const [showLog, setShowLog] = useState(false);
  const [showTopup, setShowTopup] = useState(false);
  const [startedAt, setStartedAt] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const startedRef = useRef(false);

  const videoId = extractVideoId(url);
  useEffect(() => {
    if (!videoId) return;
    const controller = new AbortController();
    fetchVideoInfo(videoId, controller.signal).then((info) => {
      if (!controller.signal.aborted) setVideoInfo(info);
    });
    return () => controller.abort();
  }, [videoId]);

  const onLog = useCallback(
    (message: string) => {
      setLogLines((prev) => [...prev, { level: levelForMessage(message), message, ts: Date.now() }]);
      const step = transition(message);
      if (!step) return;
      setClips((prev) =>
        prev.map((c, i) => {
          // On a retry the worker walks past what this page already finished.
          // That clip was made here, not earlier, so it stays "done".
          if (i !== step.index || c.status === "done") return c;
          if (step.next === "done") return { status: "done", stage: "save" };
          if (step.next === "skipped") return { status: "skipped", stage: "save" };
          return { status: "running", stage: settle(step.next, stages) };
        }),
      );
    },
    // stages only depends on options, which never change during a run.
    [],
  );

  const run = useCallback(async () => {
    const blocker = aiBlocker(config.ai, { activated, account, inappSupported: inappSupported(appInfo) });
    if (blocker) {
      setFailure({ kind: "blocker", blocker });
      setRunning(false);
      if (blocker.kind === "no-balance") setShowTopup(true);
      return;
    }

    try {
      const hookStyle = config.hookStyle;
      const watermarkConfig = config.watermark;
      const creditConfig = config.creditWatermark;
      const paddingConfig = config.clipPadding;

      const result = (await processClips({
        url,
        highlights,
        sessionDir,
        options,
        ai: {
          ...buildAIRequest(config.ai),
          temperature: 1.0,
          hook_style: {
            font_name: hookStyle.fontName,
            font_path: hookStyle.fontPath,
            font_size: hookStyle.fontSize,
            font_color: hookStyle.fontColor,
            bg_color: hookStyle.bgColor,
            corner_radius: hookStyle.cornerRadius,
            position_x: hookStyle.positionX,
            position_y: hookStyle.positionY,
            duration_seconds: hookStyle.durationSeconds,
          },
          watermark: {
            image_path: watermarkConfig.imagePath,
            position_x: watermarkConfig.positionX,
            position_y: watermarkConfig.positionY,
            opacity: watermarkConfig.opacity,
            scale: watermarkConfig.scale,
          },
          credit_watermark: {
            text: creditConfig.text,
            color: creditConfig.color,
            font_size: creditConfig.fontSize,
            opacity: creditConfig.opacity,
            position_x: creditConfig.positionX,
            position_y: creditConfig.positionY,
          },
          clip_padding: {
            lead_in: paddingConfig.leadIn,
            tail_out: paddingConfig.tailOut,
          },
        },
        onLog,
      })) as {
        results?: Array<{ clip_index?: number; skipped?: boolean; duration_seconds?: number }>;
      };

      // One analytics event per clip actually rendered here. Clips skipped
      // because an earlier session already produced them are excluded.
      const format: ReframeFormat =
        options.reframeMode === "original"
          ? "original-16-9"
          : options.reframeMode === "face"
            ? "face-tracking"
            : options.centeredBackground === "blurred"
              ? "centered-blur"
              : "centered-black";
      // The worker reports the padded length, which is what the file actually
      // runs for. Older sidecars omit it, so fall back to the model's own pick,
      // which is short by the padding but better than dropping the event.
      const durationByIndex = new Map<number, number>();
      highlights.forEach((h) => {
        const idx = (h as { _highlight_index?: number })._highlight_index;
        const dur = (h as { duration_seconds?: number }).duration_seconds;
        if (typeof idx === "number" && typeof dur === "number") durationByIndex.set(idx, dur);
      });
      const processed = Array.isArray(result?.results) ? result.results : [];
      for (const r of processed) {
        if (r?.skipped) continue;
        const dur = r?.duration_seconds ?? durationByIndex.get(r?.clip_index ?? -1);
        if (typeof dur !== "number" || dur <= 0) continue;
        trackClipRendered({ durationSeconds: dur, format });
      }

      // Anything the log did not mark (an older sidecar's wording) is done too.
      setClips((prev) => prev.map((c) => (c.status === "skipped" ? c : { status: "done", stage: "save" })));
      setIsComplete(true);
    } catch (err) {
      const detail = err instanceof Error ? err.message : typeof err === "string" ? err : JSON.stringify(err);
      console.error("process_clips failed", err);
      setClips((prev) => prev.map((c) => (c.status === "running" ? { ...c, status: "error" } : c)));
      // The balance can run dry mid-run, since one job is many requests. Say
      // so plainly and put the top-up in front of the user.
      if (config.ai.source === "inapp" && isOutOfBalance(err)) {
        setFailure({ kind: "balance" });
        setShowTopup(true);
        void refreshAccount();
      } else {
        setFailure({ kind: "error", detail });
        setShowLog(true);
      }
    } finally {
      setRunning(false);
    }
  }, [url, highlights, sessionDir, options, config.ai, config.hookStyle, config.watermark, config.creditWatermark, config.clipPadding, activated, account, appInfo, refreshAccount, onLog]);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    void run();
  }, [run]);

  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [running, startedAt]);

  const retry = () => {
    setFailure(null);
    setIsComplete(false);
    setShowLog(false);
    setLogLines([]);
    // Finished clips stay finished: the worker skips them on the next run.
    setClips((prev) => prev.map((c) => (c.status === "done" || c.status === "skipped" ? c : { status: "waiting", stage: "download" })));
    setStartedAt(Date.now());
    setElapsed(0);
    setRunning(true);
    void run();
  };

  const finished = clips.filter((c) => c.status === "done" || c.status === "skipped").length;
  const skipped = clips.filter((c) => c.status === "skipped").length;
  const currentIndex = clips.findIndex((c) => c.status === "running");
  const current = currentIndex >= 0 ? clips[currentIndex] : null;
  // Each clip counts in equal parts; inside a clip, each stage does too.
  const partial = current ? stages.indexOf(current.stage) / stages.length : 0;
  const percent = isComplete ? 100 : Math.round(((finished + partial) / Math.max(1, total)) * 100);

  const titleOf = (i: number) => (highlights[i] as { title?: string })?.title || t("renderPage.clipOf", { n: i + 1, total });
  const stageBody = (stage: Stage) =>
    stage === "reframe"
      ? t(`renderPage.stages.reframe.${options.reframeMode === "face" ? "face" : "centered"}`)
      : t(`renderPage.stages.${stage}.body`);

  return (
    <div className="mx-auto max-w-[760px] py-4">
      {/* Which video this is about */}
      <div className="flex items-center gap-4">
        {videoId && (
          <img
            src={getThumbnailUrl(videoId, "mq")}
            alt=""
            className="aspect-video w-28 shrink-0 rounded-[var(--radius-sm)] border border-[var(--color-border)] object-cover"
          />
        )}
        <div className="min-w-0">
          <p className="text-sm text-[var(--color-text-muted)]">
            {failure ? t("renderPage.errorTitle") : isComplete ? t("renderPage.doneTitle") : t("renderPage.title")}
            {" · "}
            {t(`renderPage.shape.${options.reframeMode}`)}
          </p>
          <p className="mt-0.5 line-clamp-2 text-lg font-semibold text-[var(--color-text-primary)] leading-snug">
            {videoInfo?.title ?? url}
          </p>
        </div>
      </div>

      {/* Overall progress */}
      <div className="mt-8">
        <div className="flex items-baseline justify-between gap-4">
          <p className="text-sm font-medium text-[var(--color-text-primary)]">
            {t("renderPage.progress", { done: finished, total })}
          </p>
          <p className="text-xs tabular-nums text-[var(--color-text-muted)]">
            {running ? t("renderPage.elapsed", { time: clock(elapsed) }) : `${percent}%`}
          </p>
        </div>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label={t("renderPage.progress", { done: finished, total })}
          className="mt-2.5 h-2 overflow-hidden rounded-full bg-[var(--color-bg-hover)]"
        >
          <div
            className={cn(
              "h-full rounded-full transition-[width] duration-700 ease-out",
              failure ? "bg-[var(--color-text-muted)]" : isComplete ? "bg-[var(--color-success)]" : "bg-[var(--color-accent)]",
            )}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      {/* What is happening right now, or how it ended */}
      <section
        aria-live="polite"
        className={cn(
          "mt-6 rounded-[var(--radius-lg)] border p-5",
          failure ? "border-[var(--color-error)]/40 bg-[var(--color-error-bg)]" : "border-[var(--color-border)] bg-[var(--color-bg-primary)]",
        )}
      >
        {failure ? (
          <FailurePanel
            failure={failure}
            hasFinished={finished > 0}
            onRetry={retry}
            onTopUp={() => setShowTopup(true)}
            onOpenAi={() => navigate("/ai-models")}
            onOpenLibrary={() => navigate(clipsUrl)}
          />
        ) : isComplete ? (
          <>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">{t("renderPage.doneTitle")}</p>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">
              {t("renderPage.done", { count: total })}
              {skipped > 0 && ` ${t("renderPage.doneSkipped", { count: skipped })}`}
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Button onClick={() => navigate(clipsUrl)} className="h-11 gap-2 px-6 text-base font-semibold">
                {t("renderPage.openLibrary")}
                <ArrowRight aria-hidden className="h-4 w-4" />
              </Button>
              <Button variant="outline" onClick={() => navigate("/")} className="h-11 px-5">
                {t("renderPage.makeMore")}
              </Button>
            </div>
          </>
        ) : current ? (
          <>
            <p className="text-xs font-medium text-[var(--color-text-muted)]">
              {t("renderPage.clipOf", { n: currentIndex + 1, total })}
              {" · "}
              <span className="text-[var(--color-text-secondary)]">{titleOf(currentIndex)}</span>
            </p>
            <p className="mt-1 text-xl font-bold text-[var(--color-text-primary)]">
              {t(`renderPage.stages.${current.stage}.title`)}
            </p>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{stageBody(current.stage)}</p>
            <StageTrack stages={stages} current={current.stage} />
            <p className="mt-4 text-xs text-[var(--color-text-muted)]">{t("renderPage.keepOpen")}</p>
          </>
        ) : (
          <>
            <p className="text-xl font-bold text-[var(--color-text-primary)]">
              {finished === 0 ? t("renderPage.preparing") : t("renderPage.wrappingUp")}
            </p>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">
              {finished === 0 ? t("renderPage.preparingBody") : t("renderPage.wrappingUpBody")}
            </p>
            <p className="mt-4 text-xs text-[var(--color-text-muted)]">{t("renderPage.keepOpen")}</p>
          </>
        )}
      </section>

      {/* Every clip and where it is */}
      <ol className="mt-6 divide-y divide-[var(--color-border)] rounded-[var(--radius-lg)] border border-[var(--color-border)]">
        {clips.map((clip, i) => (
          <li key={i} className="flex items-center gap-3 px-4 py-3">
            <ClipBadge clip={clip} n={i + 1} />
            <p
              className={cn(
                "min-w-0 flex-1 truncate text-sm",
                clip.status === "running" ? "font-semibold text-[var(--color-text-primary)]" : "text-[var(--color-text-secondary)]",
              )}
            >
              {titleOf(i)}
            </p>
            <span
              className={cn(
                "shrink-0 text-xs",
                clip.status === "running"
                  ? "text-[var(--color-accent)]"
                  : clip.status === "done"
                    ? "text-[var(--color-success)]"
                    : clip.status === "error"
                      ? "text-[var(--color-error)]"
                      : "text-[var(--color-text-muted)]",
              )}
            >
              {clip.status === "running" ? t(`renderPage.stages.${clip.stage}.title`) : t(`renderPage.status.${clip.status}`)}
            </span>
          </li>
        ))}
      </ol>

      <TechnicalLog lines={logLines} open={showLog} onToggle={() => setShowLog((v) => !v)} />

      {showTopup && (
        <TopupDialog
          onClose={() => {
            setShowTopup(false);
            void refreshAccount();
          }}
        />
      )}
    </div>
  );
}

/** The current clip's stages as a row of short segments: done, now, still to go. */
function StageTrack({ stages, current }: { stages: Stage[]; current: Stage }) {
  const { t } = useTranslation();
  const at = stages.indexOf(current);
  return (
    <ol className="mt-5 flex gap-1.5" aria-label={t(`renderPage.stages.${current}.title`)}>
      {stages.map((stage, i) => (
        <li key={stage} className="min-w-0 flex-1" title={t(`renderPage.stages.${stage}.title`)}>
          <span
            className={cn(
              "block h-1.5 rounded-full",
              i < at
                ? "bg-[var(--color-success)]"
                : i === at
                  ? "bg-[var(--color-accent)] motion-safe:animate-pulse"
                  : "bg-[var(--color-bg-hover)]",
            )}
          />
        </li>
      ))}
    </ol>
  );
}

function ClipBadge({ clip, n }: { clip: ClipState; n: number }) {
  const base = "relative flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold";
  if (clip.status === "done" || clip.status === "skipped") {
    return (
      <span className={cn(base, "bg-[var(--color-success)] text-[var(--color-bg-primary)]")}>
        <Check aria-hidden className="h-3.5 w-3.5" strokeWidth={3} />
      </span>
    );
  }
  if (clip.status === "error") {
    return (
      <span className={cn(base, "bg-[var(--color-error)] text-[var(--color-bg-primary)]")}>
        <X aria-hidden className="h-3.5 w-3.5" strokeWidth={3} />
      </span>
    );
  }
  if (clip.status === "running") {
    return (
      <span className={cn(base, "text-[var(--color-accent)]")}>
        <svg aria-hidden viewBox="0 0 28 28" className="absolute inset-0 h-7 w-7 motion-safe:animate-spin [animation-duration:1.1s]">
          <circle cx="14" cy="14" r="12" fill="none" stroke="var(--color-border)" strokeWidth="2" />
          <circle cx="14" cy="14" r="12" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeDasharray="20 76" />
        </svg>
        {n}
      </span>
    );
  }
  return <span className={cn(base, "border border-[var(--color-border)] text-[var(--color-text-muted)]")}>{n}</span>;
}

function FailurePanel({
  failure,
  hasFinished,
  onRetry,
  onTopUp,
  onOpenAi,
  onOpenLibrary,
}: {
  failure: Failure;
  hasFinished: boolean;
  onRetry: () => void;
  onTopUp: () => void;
  onOpenAi: () => void;
  onOpenLibrary: () => void;
}) {
  const { t } = useTranslation();
  const reason =
    failure.kind === "balance"
      ? t("renderPage.outOfBalance")
      : failure.kind === "error"
        ? shortError(failure.detail)
        : failure.blocker.kind === "account-blocked"
          ? failure.blocker.detail
          : t(`renderPage.blocker.${failure.blocker.kind}`);
  const needsTopUp = failure.kind === "balance" || (failure.kind === "blocker" && failure.blocker.kind === "no-balance");
  const needsAiSetup = failure.kind === "blocker" && !needsTopUp && failure.blocker.kind !== "account-blocked";

  return (
    <>
      <p className="text-base font-semibold text-[var(--color-text-primary)]">{t("renderPage.errorTitle")}</p>
      <p className="mt-2 whitespace-pre-line break-words text-sm text-[var(--color-error)]">{reason}</p>
      {failure.kind !== "blocker" && (
        <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("renderPage.errorBody")}</p>
      )}
      <div className="mt-5 flex flex-wrap gap-3">
        {needsTopUp ? (
          <Button onClick={onTopUp} className="h-11 px-5">
            {t("renderPage.topUp")}
          </Button>
        ) : needsAiSetup ? (
          <Button onClick={onOpenAi} className="h-11 px-5">
            {t("renderPage.setUpAi")}
          </Button>
        ) : null}
        <Button variant={needsTopUp || needsAiSetup ? "outline" : "default"} onClick={onRetry} className="h-11 px-5">
          {t("renderPage.retry")}
        </Button>
        {hasFinished && (
          <Button variant="outline" onClick={onOpenLibrary} className="h-11 px-5">
            {t("renderPage.openLibrary")}
          </Button>
        )}
      </div>
    </>
  );
}
