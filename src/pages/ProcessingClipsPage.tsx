import { useEffect, useRef, useCallback, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Loader2, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { processClips, type ProcessOptions } from "@/hooks/processClips";
import { logClipSuccess, type ClipSuccessFormat } from "@/hooks/successLog";
import { useConfigStore } from "@/stores/configStore";
import { formatLogTime } from "@/utils/format";

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
  const state = location.state as ClipProcessingState | undefined;

  if (!state) {
    navigate("/");
    return null;
  }

  const { url, highlights, sessionDir, options } = state;
  const [logLines, setLogLines] = useState<{ level: string; message: string; ts: number }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0); // 0=download, 1=portrait, 2=hook, 3=caption, 4=watermark
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [copied, setCopied] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);
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

  const startedRef = useRef(false);

  const appendLog = useCallback((message: string) => {
    const m = message.toLowerCase();
    const level = m.includes("error") || m.includes("failed") ? "error"
      : m.includes("success") || m.includes("complete") || m.includes("saved") ? "success"
      : "info";
    setLogLines((prev) => [...prev, { level, message, ts: Date.now() }]);
  }, []);

  // Auto-progress based on log patterns
  useEffect(() => {
    const lastLog = (logLines[logLines.length - 1]?.message || "").toLowerCase();

    if (lastLog.includes("section downloaded")) {
      setCurrentStep(1);
    }
    if (lastLog.includes("portrait conversion complete") || lastLog.includes("portrait complete")) {
      setCurrentStep(2);
    }
    if (lastLog.includes("hook generation complete") || lastLog.includes("hook complete") || lastLog.includes("hook generation skipped")) {
      setCurrentStep(3);
    }
    if (lastLog.includes("caption generation complete") || lastLog.includes("caption complete") || lastLog.includes("caption generation skipped")) {
      setCurrentStep(4);
    }
    if (lastLog.includes("watermark") && lastLog.includes("complete")) {
      setCurrentStep(5);
    }

    const clipsSaved = logLines.filter((l) => l.message.toLowerCase().includes("clip saved")).length;
    if (clipsSaved > 0 && highlights.length > 0) {
      setProgress(Math.min(95, Math.round((clipsSaved / highlights.length) * 95)));
    }
  }, [logLines, highlights.length]);

  const run = useCallback(async () => {
    const hf = config.ai;
    if (!hf.apiKey || !hf.model) {
      setError("AI provider not configured. Please set it up in AI Models first.");
      return;
    }

    appendLog("Starting clip processing...");

    try {
      const hookStyle = config.hookStyle;
      const watermarkConfig = config.watermark;
      const creditConfig = config.creditWatermark;

      const result = (await processClips({
        url,
        highlights,
        sessionDir,
        options,
        ai: {
          api_key: hf.apiKey,
          base_url: hf.baseUrl,
          model: hf.model,
          system_message: hf.systemMessage,
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
          appendLog(message);
          const m = message.toLowerCase();
          // Step transitions happen when a step COMPLETES, not when it starts
          if (m.includes("section downloaded")) {
            setCurrentStep(1); // Download done → now doing Portrait
          } else if (m.includes("portrait conversion complete") || m.includes("portrait complete")) {
            setCurrentStep(2); // Portrait done → now doing Hook
          } else if (m.includes("hook generation complete") || m.includes("hook complete") || m.includes("hook generation skipped")) {
            setCurrentStep(3); // Hook done → now doing Caption
          } else if (m.includes("caption generation complete") || m.includes("caption complete") || m.includes("caption generation skipped")) {
            setCurrentStep(4); // Caption done → now doing Watermark
          } else if (m.includes("watermark") && m.includes("complete")) {
            setCurrentStep(5); // Watermark done
          }
          if (m.includes("all") && m.includes("processed")) {
            setProgress(100);
            setIsComplete(true);
          }
        },
      }) as { results?: Array<{ clip_index?: number; skipped?: boolean }> });

      // Fire telemetry webhook: one request per successfully processed clip
      // (skipped clips were processed in an earlier session and are excluded).
      const format: ClipSuccessFormat =
        options.reframeMode === "face"
          ? "face-tracking"
          : options.centeredBackground === "blurred"
            ? "centered-blur"
            : "centered-black";
      const durationByIndex = new Map<number, number>();
      highlights.forEach((h) => {
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

      setIsComplete(true);
      setProgress(100);
      appendLog("✅ All clips processed successfully!");
    } catch (err) {
      const detail = err instanceof Error ? err.message : typeof err === "string" ? err : JSON.stringify(err);
      console.error("process_clips failed", err);
      setError(detail);
      appendLog(`❌ Error: ${detail}`);
    }
  }, [url, highlights, sessionDir, options, config.ai, config.hookStyle, config.watermark, config.creditWatermark, appendLog, navigate]);

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
        disabled={!isComplete}
      >
        <ArrowLeft className="w-4 h-4" />
        {isComplete ? "Back to Create" : "Processing..."}
      </Button>

      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
          {isComplete ? "✅ Processing complete!" : "Processing clips..."}
        </h2>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          {isComplete
            ? "All clips have been processed and saved."
            : `Processing ${highlights.length} clips with selected enhancements.`}
        </p>
      </div>

      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-[var(--color-text-secondary)]">Progress</span>
          <span className="text-sm text-[var(--color-text-muted)]">{Math.round(progress)}%</span>
        </div>
        <Progress value={progress} />
      </div>

      {/* Steps summary */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3">Enhancements</h3>
        <div className="space-y-2">
          {[
            { label: "Download video sections", step: 0 },
            { label: "Portrait conversion (9:16)", step: 1 },
            { label: "Hook generation", step: 2, required: options.addHook },
            { label: "Caption generation", step: 3, required: options.addCaptions },
            { label: "Watermark overlay", step: 4, required: options.addWatermark || options.addCreditWatermark },
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

      {error && (
        <Button onClick={() => navigate("/")} variant="outline" className="w-full">
          Back to Create
        </Button>
      )}

      {isComplete && !error && (
        <div className="flex gap-3">
          <Button onClick={() => navigate("/")} variant="outline" className="flex-1">
            Back to Create
          </Button>
          <Button onClick={() => navigate("/library")} className="flex-1">
            Go to Library
          </Button>
        </div>
      )}
    </div>
  );
}
