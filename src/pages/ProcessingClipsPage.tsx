import { useEffect, useRef, useCallback, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Copy,
  Check,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { processClips, type ProcessOptions } from "@/hooks/processClips";
import { logClipSuccess, type ClipSuccessFormat } from "@/hooks/successLog";
import { useConfigStore } from "@/stores/configStore";
import { useAppStore } from "@/stores/appStore";
import { useProcessingClipsStore } from "@/stores/processingClipsStore";
import { formatLogTime } from "@/utils/format";
import { cn } from "@/lib/utils";

interface ClipProcessingState {
  url: string;
  highlights: unknown[];
  sessionDir: string;
  options: ProcessOptions;
}

export function ProcessingClipsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { config } = useConfigStore();
  const { showLogs, toggleShowLogs } = useAppStore();

  // Live view of the persistent session store — survives navigating away/back.
  const logLines = useProcessingClipsStore((s) => s.logLines);
  const currentStep = useProcessingClipsStore((s) => s.currentStep);
  const progress = useProcessingClipsStore((s) => s.progress);
  const isComplete = useProcessingClipsStore((s) => s.isComplete);
  const error = useProcessingClipsStore((s) => s.error);
  const initialized = useProcessingClipsStore((s) => s.initialized);
  const active = useProcessingClipsStore((s) => s.active);
  const highlights = useProcessingClipsStore((s) => s.highlights);

  const state = location.state as ClipProcessingState | undefined;
  const options = useProcessingClipsStore((s) => s.options);
  const isSplitScreen = !!options?.splitScreen?.enabled;

  const [copied, setCopied] = useState(false);
  const [completedClips, setCompletedClips] = useState(0);
  const logEndRef = useRef<HTMLDivElement>(null);
  const startedRef = useRef(false);

  const copyLog = useCallback(async () => {
    const text = logLines
      .map((l) => `[${formatLogTime(l.ts)}] ${l.level.toUpperCase()}: ${l.message}`)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // silent
    }
  }, [logLines]);

  const run = useCallback(async () => {
    const store = useProcessingClipsStore.getState();
    if (!store.initialized || !store.url) return;
    const { url, highlights: hls, sessionDir, options } = store;

    if (!config.ai.apiKey || !config.ai.model) {
      store.setError("AI provider not configured. Please set it up in AI Models first.");
      return;
    }

    store.appendLog("Starting clip processing...");

    try {
      const hookStyle = config.hookStyle;
      const watermarkConfig = config.watermark;
      const creditConfig = config.creditWatermark;

      const result = (await processClips({
        url,
        highlights: hls,
        sessionDir,
        options,
        ai: {
          api_key: config.ai.apiKey,
          base_url: config.ai.baseUrl,
          model: config.ai.model,
          system_message: config.ai.systemMessage,
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
        },
        onLog: (message) => {
          const st = useProcessingClipsStore.getState();
          st.appendLog(message);
          const m = message.toLowerCase();

          // Real-time encoding progress (portrait conversion) — fires repeatedly during encoding
          const encMatch = m.match(/encoding portrait:\s*(\d+)%/);
          if (encMatch) {
            const encPct = Number(encMatch[1]);
            if (encPct > 0) {
              // Map encoding progress to overall progress (0-90% for encoding, rest for other steps)
              // Assuming encoding is the bulk of work, cap at 90% until clip saved
              const overall = Math.min(90, Math.round((completedClips / highlights.length) * 90) + Math.round((encPct / 100) * (90 / highlights.length)));
              st.setProgress(overall);
            }
          }

          // Split-screen composition progress
          if (m.includes("composing split screen")) {
            // Split screen is the final video composition step (~90-95%)
            st.setProgress(Math.min(95, st.progress + 5));
          }

          // Per-clip progress: when a clip is fully saved, bump the progress bar
          const clipMatch = m.match(/\[(\d+)\/(\d+)\]/);
          if (clipMatch && m.includes("clip saved")) {
            const done = Number(clipMatch[1]);
            const total = Number(clipMatch[2]);
            if (total > 0) {
              setCompletedClips(done);
              st.setProgress(Math.min(99, Math.round((done / total) * 100)));
            }
          }
          // Step transitions happen when a step COMPLETES, not when it starts
          if (m.includes("section downloaded")) {
            st.setStep(1);
          } else if (
            m.includes("portrait conversion complete") ||
            m.includes("portrait complete") ||
            m.includes("split screen composition complete") ||
            m.includes("split-screen composition complete")
          ) {
            st.setStep(2);
          } else if (
            m.includes("hook generation complete") ||
            m.includes("hook complete") ||
            m.includes("hook generation skipped")
          ) {
            st.setStep(3);
          } else if (
            m.includes("caption generation complete") ||
            m.includes("caption complete") ||
            m.includes("caption generation skipped")
          ) {
            st.setStep(4);
          } else if (m.includes("watermark") && m.includes("complete")) {
            st.setStep(5);
          }
          if (m.includes("all") && m.includes("processed")) {
            st.setProgress(100);
            st.setComplete();
          }
        },
      }) as { results?: Array<{ clip_index?: number; skipped?: boolean }> });

      // Fire telemetry webhook: one request per successfully processed clip
      // (skipped clips were processed in an earlier session and are excluded).
      const format: ClipSuccessFormat =
        isSplitScreen
          ? "split-screen"
          : options.reframeMode === "face"
            ? "face-tracking"
            : options.centeredBackground === "blurred"
              ? "centered-blur"
              : "centered-black";
      const durationByIndex = new Map<number, number>();
      hls.forEach((h) => {
        const idx = (h as { _highlight_index?: number })._highlight_index;
        const dur = (h as { duration_seconds?: number }).duration_seconds;
        if (typeof idx === "number" && typeof dur === "number") durationByIndex.set(idx, dur);
      });
      const processed = Array.isArray(result?.results) ? result.results : [];
      for (const r of processed) {
        if (r?.skipped) continue;
        const dur = durationByIndex.get(r?.clip_index ?? -1);
        if (typeof dur !== "number" || dur <= 0) continue;
        void logClipSuccess({ duration: dur, format });
      }

      const st = useProcessingClipsStore.getState();
      st.setComplete();
      st.appendLog("✅ All clips processed successfully!");
    } catch (err) {
      const detail =
        err instanceof Error ? err.message : typeof err === "string" ? err : JSON.stringify(err);
      console.error("process_clips failed", err);
      const st = useProcessingClipsStore.getState();
      st.setError(detail);
      st.appendLog(`❌ Error: ${detail}`);
    }
  }, [config, isSplitScreen]);

  // Bootstrap: restore an existing session OR start a fresh one from location.state.
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const store = useProcessingClipsStore.getState();
    if (store.initialized) {
      // Session already exists (user navigated away and came back) — the
      // sidecar invoke keeps running in the background; just resume the view.
      return;
    }

    if (!state) {
      navigate("/");
      return;
    }

    const { url, highlights: hls, sessionDir, options } = state;
    store.start({ url, highlights: hls, sessionDir, options });
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logLines]);

  const title = error
    ? "Something went wrong"
    : isComplete
      ? "✅ Processing complete!"
      : active
        ? "Processing clips..."
        : initialized
          ? "Processing paused"
          : "Processing clips...";

  const subtitle = error
    ? "Review the log below and try again."
    : isComplete
      ? "All clips have been processed and saved."
      : `Processing ${highlights.length} clips with selected enhancements.`;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="ghost"
          onClick={() => navigate("/")}
          className="gap-2 text-[var(--color-text-secondary)]"
          disabled={!isComplete && !error && active}
        >
          <ArrowLeft className="w-4 h-4" />
          {isComplete || error ? "Back to Create" : "Processing..."}
        </Button>

        {/* Log on/off toggle — always visible on this page */}
        <Button
          variant="outline"
          size="sm"
          onClick={toggleShowLogs}
          className={cn(
            "gap-2",
            showLogs ? "text-[var(--color-accent)]" : "text-[var(--color-text-muted)]"
          )}
          title={showLogs ? "Hide log console" : "Show log console"}
        >
          {showLogs ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
          {showLogs ? "Log: On" : "Log: Off"}
        </Button>
      </div>

      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{title}</h2>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">{subtitle}</p>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-[var(--color-text-secondary)]">Progress</span>
          <span className="text-sm text-[var(--color-text-muted)]">
            {highlights.length > 0 && completedClips > 0 && !isComplete
              ? `${completedClips}/${highlights.length} selesai · `
              : ""}
            {Math.round(progress)}%
          </span>
        </div>
        <Progress value={progress} />
      </div>

      {/* Steps summary */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Enhancements</h3>
        <div className="space-y-2">
          {[
            { label: "Download video sections", step: 0 },
            {
              label: isSplitScreen ? "Split screen composition (9:16)" : "Portrait conversion (9:16)",
              step: 1,
            },
            { label: "Hook generation", step: 2, required: options?.addHook },
            { label: "Caption generation", step: 3, required: options?.addCaptions },
            {
              label: "Watermark overlay",
              step: 4,
              required: options?.addWatermark || options?.addCreditWatermark,
            },
          ].map((item, i) => {
            const isActive = currentStep === item.step;
            const isDone = currentStep > item.step;
            const skip = item.required === false;

            return (
              <div key={i} className="flex items-center gap-3">
                {skip ? (
                  <span className="w-5 h-5 shrink-0 flex items-center justify-center text-[var(--color-text-muted)] text-xs">—</span>
                ) : isDone ? (
                  <CheckCircle2 className="w-5 h-5 text-[var(--color-success)] shrink-0" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 text-[var(--color-accent)] animate-spin shrink-0" />
                ) : (
                  <Loader2 className="w-5 h-5 text-[var(--color-text-muted)] shrink-0 opacity-30" />
                )}
                <span className={`text-sm ${
                  isDone ? "text-[var(--color-success)]"
                    : isActive ? "text-[var(--color-accent)] font-medium"
                    : skip ? "text-[var(--color-text-muted)] line-through"
                    : "text-[var(--color-text-muted)]"
                }`}>
                  {item.label}{skip ? " (skipped)" : ""}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Log console — hidden by the page-level Log toggle */}
      {showLogs && (
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
                    line.level === "error" ? "text-[var(--color-error)]"
                      : line.level === "success" ? "text-[var(--color-success)]"
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
      )}

      {(error || isComplete) && (
        <div className="flex gap-3">
          <Button
            onClick={() => {
              useProcessingClipsStore.getState().reset();
              navigate("/");
            }}
            variant="outline"
            className="flex-1"
          >
            Back to Create
          </Button>
          {isComplete && !error && (
            <Button
              onClick={() => {
                useProcessingClipsStore.getState().reset();
                navigate("/library");
              }}
              className="flex-1"
            >
              Go to Library
            </Button>
          )}
        </div>
      )}
    </div>
  );
}