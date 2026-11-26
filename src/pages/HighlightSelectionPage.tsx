import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft,
  CheckSquare,
  Square,
  Flame,
  Zap,
  Sparkle,
  Quote,
  Film,
  FolderOpen,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  RotateCw,
  Volume2,
  VolumeX,
  ZoomIn,
  ZoomOut,
  Undo2,
  Loader2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { Button } from "@/components/ui/button";
import { useSessionStore } from "@/stores/sessionStore";
import { useConfigStore } from "@/stores/configStore";
import type { Highlight } from "@/hooks/highlights";
import { ProcessConfirmDialog } from "@/components/ProcessConfirmDialog";
import { Timeline, MIN_CLIP_SECONDS } from "@/components/editor/Timeline";
import { ensureProxy, useProxyStore } from "@/hooks/proxy";
import { useTranscript, textInRange, type TimedToken } from "@/hooks/transcript";
import { formatClock, parseTimestamp } from "@/lib/timecode";

const ZOOM_LEVELS = [0.35, 0.7, 1.5, 3, 6];
const DEFAULT_ZOOM = 1;

function viralityStyle(score: number) {
  if (score >= 7) return { color: "var(--color-success)", Icon: Flame };
  if (score >= 5) return { color: "var(--color-warning)", Icon: Zap };
  return { color: "var(--color-text-muted)", Icon: Sparkle };
}

function rangeOf(h: Highlight) {
  return { start: parseTimestamp(h.start_time), end: parseTimestamp(h.end_time) };
}

function isEdited(h: Highlight) {
  return (
    !!h.original_start_time &&
    (h.original_start_time !== h.start_time || h.original_end_time !== h.end_time)
  );
}

function clipPathFor(sessionDir: string, index: number) {
  return `${sessionDir}\\clips\\clip_${String(index).padStart(3, "0")}\\master.mp4`;
}

export function HighlightSelectionPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    session,
    origin,
    selectedIndices,
    toggleSelected,
    selectAll,
    deselectAll,
    getSelectedHighlights,
    trimHighlight,
    resetHighlight,
  } = useSessionStore();
  const clipPadding = useConfigStore((s) => s.config.clipPadding);

  const [showProcessDialog, setShowProcessDialog] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!session) navigate("/");
  }, [session, navigate]);

  // Start (or resume watching) the preview download as soon as the page opens.
  useEffect(() => {
    if (session) void ensureProxy(session.url, session.session_dir);
  }, [session?.url, session?.session_dir]); // eslint-disable-line react-hooks/exhaustive-deps

  const proxy = useProxyStore((s) => (session ? s.bySession[session.session_dir] : undefined));
  const transcript = useTranscript(
    session?.session_dir ?? "",
    session?.srt_path ?? "",
    session?.caption_words_path,
  );

  if (!session) return null;

  // The sidecar never saves a session without highlights, but a damaged or
  // hand-edited session file could; show that instead of crashing the editor.
  if (session.highlights.length === 0) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <p className="text-base font-semibold text-[var(--color-text-primary)]">{t("highlightsEmpty.title")}</p>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{t("highlightsEmpty.body")}</p>
        <Button variant="outline" onClick={() => navigate(origin === "library" ? "/library" : "/")} className="mt-6 h-11 px-5">
          {t("highlightsEmpty.back")}
        </Button>
      </div>
    );
  }

  const highlights = session.highlights;
  const processedSet = new Set(session.processed_highlights ?? []);
  const selectedCount = [...selectedIndices].filter((i) => !processedSet.has(i)).length;
  const safeIndex = Math.min(activeIndex, highlights.length - 1);
  const backTo = origin === "library" ? "/library" : "/";

  return (
    <div className="h-full flex flex-col gap-3 p-4 min-h-0">
      <header className="flex items-center gap-3 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(backTo)}
          aria-label={t("editor.backLabel")}
          className="h-9 gap-1.5 text-[var(--color-text-secondary)] shrink-0"
        >
          <ArrowLeft aria-hidden className="w-4 h-4" />
          {origin === "library" ? t("editor.backToProjects") : t("editor.backToCreate")}
        </Button>
        <span aria-hidden className="text-[var(--color-text-muted)]">/</span>
        <h1 className="flex-1 min-w-0 truncate text-sm font-semibold text-[var(--color-text-primary)]">
          {session.video_info.title || t("editor.untitled")}
        </h1>
        <Button variant="ghost" size="sm" onClick={selectAll} className="h-9 shrink-0">
          {t("editor.selectAll")}
        </Button>
        <Button variant="ghost" size="sm" onClick={deselectAll} className="h-9 shrink-0">
          {t("editor.clearSelection")}
        </Button>
        <Button
          size="sm"
          disabled={selectedCount === 0}
          onClick={() => setShowProcessDialog(true)}
          className="h-9 gap-1.5 shrink-0 px-4"
        >
          <Film aria-hidden className="w-4 h-4" />
          {t("editor.render", { count: selectedCount })}
        </Button>
      </header>

      <Editor
        key={session.session_dir}
        highlights={highlights}
        activeIndex={safeIndex}
        setActiveIndex={setActiveIndex}
        selectedIndices={selectedIndices}
        processedSet={processedSet}
        sessionDir={session.session_dir}
        projectTitle={session.video_info?.title}
        proxy={proxy}
        retryProxy={() => void ensureProxy(session.url, session.session_dir)}
        tokens={transcript?.tokens ?? []}
        transcriptLoaded={!!transcript}
        padding={clipPadding}
        onToggle={(i) => {
          if (!processedSet.has(i)) toggleSelected(i);
        }}
        onTrim={(i, start, end) =>
          trimHighlight(i, {
            start,
            end,
            transcriptText: transcript ? textInRange(transcript.tokens, start, end) : undefined,
          })
        }
        onReset={(i) => {
          const h = highlights[i];
          if (!h.original_start_time || !h.original_end_time) return;
          const s = parseTimestamp(h.original_start_time);
          const e = parseTimestamp(h.original_end_time);
          resetHighlight(i, transcript ? textInRange(transcript.tokens, s, e) : undefined);
        }}
      />

      {showProcessDialog && (
        <ProcessConfirmDialog
          clipCount={selectedCount}
          captionsAvailable={session.caption_available ?? true}
          onConfirm={(options) => {
            setShowProcessDialog(false);
            const selected = getSelectedHighlights();
            const highlightsWithIndex = selected
              .map((h) => ({ ...h, _highlight_index: highlights.indexOf(h) }))
              .filter((h) => !processedSet.has(h._highlight_index));
            navigate("/processing-clips", {
              state: {
                url: session.url,
                highlights: highlightsWithIndex,
                sessionDir: session.session_dir,
                options,
              },
            });
          }}
          onCancel={() => setShowProcessDialog(false)}
        />
      )}
    </div>
  );
}

interface EditorProps {
  highlights: Highlight[];
  activeIndex: number;
  setActiveIndex: (i: number) => void;
  selectedIndices: Set<number>;
  processedSet: Set<number>;
  sessionDir: string;
  projectTitle?: string;
  proxy: ReturnType<typeof useProxyStore.getState>["bySession"][string] | undefined;
  retryProxy: () => void;
  tokens: TimedToken[];
  transcriptLoaded: boolean;
  padding: { leadIn: number; tailOut: number };
  onToggle: (i: number) => void;
  onTrim: (i: number, start: number, end: number) => void;
  onReset: (i: number) => void;
}

function Editor({
  highlights,
  activeIndex,
  setActiveIndex,
  selectedIndices,
  processedSet,
  sessionDir,
  projectTitle,
  proxy,
  retryProxy,
  tokens,
  transcriptLoaded,
  padding,
  onToggle,
  onTrim,
  onReset,
}: EditorProps) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const [zoom, setZoom] = useState(DEFAULT_ZOOM);

  const active = highlights[activeIndex];
  const { start, end } = rangeOf(active);
  const locked = processedSet.has(activeIndex);

  const proxySrc = proxy?.status === "ready" && proxy.path ? convertFileSrc(proxy.path) : null;

  // Until the proxy reports its length, size the timeline from what we know.
  const duration = useMemo(() => {
    if (videoDuration) return videoDuration;
    const lastToken = tokens.length ? tokens[tokens.length - 1].end : 0;
    const lastClip = Math.max(...highlights.map((h) => rangeOf(h).end));
    return Math.max(lastToken, lastClip) + 30;
  }, [videoDuration, tokens, highlights]);

  // The visible window follows the clip, but holds still while a handle is
  // dragged; it re-centers when the drag ends or the zoom changes.
  const [anchor, setAnchor] = useState({ start, end });
  useEffect(() => {
    setAnchor(rangeOf(highlights[activeIndex]));
    // Only when the active clip changes, not on every trim.
  }, [activeIndex]); // eslint-disable-line react-hooks/exhaustive-deps

  const view = useMemo(() => {
    const len = anchor.end - anchor.start;
    const pad = Math.max(10, len * 0.5) * zoom;
    const vs = Math.max(0, anchor.start - pad);
    const ve = Math.min(duration, anchor.end + pad);
    return { start: vs, end: Math.max(ve, vs + 1) };
  }, [anchor, zoom, duration]);

  const seek = useCallback((time: number) => {
    const v = videoRef.current;
    setCurrentTime(time);
    if (v && v.readyState >= 1) v.currentTime = time;
  }, []);

  // Jump to the clip's start whenever another clip is chosen.
  useEffect(() => {
    videoRef.current?.pause();
    seek(rangeOf(highlights[activeIndex]).start);
  }, [activeIndex, proxySrc]); // eslint-disable-line react-hooks/exhaustive-deps

  // Smooth playhead while playing, and stop at the clip's end.
  const endRef = useRef(end);
  endRef.current = end;
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const tick = () => {
      const v = videoRef.current;
      if (v) {
        if (v.currentTime >= endRef.current) {
          v.pause();
          v.currentTime = endRef.current;
        }
        setCurrentTime(v.currentTime);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);

  const togglePlay = useCallback(() => {
    const v = videoRef.current;
    if (!v || !proxySrc) return;
    if (!v.paused) {
      v.pause();
      return;
    }
    const { start: s, end: e } = rangeOf(highlights[activeIndex]);
    if (v.currentTime < s - 0.05 || v.currentTime >= e - 0.05) v.currentTime = s;
    void v.play();
  }, [highlights, activeIndex, proxySrc]);

  const nudge = (delta: number) => seek(Math.min(duration, Math.max(0, currentTime + delta)));

  const setEdge = (edge: "start" | "end", time: number) => {
    if (locked) return;
    if (edge === "start") onTrim(activeIndex, Math.max(0, Math.min(time, end - MIN_CLIP_SECONDS)), end);
    else onTrim(activeIndex, start, Math.min(duration, Math.max(time, start + MIN_CLIP_SECONDS)));
  };

  // Keyboard: Space play, arrows seek, I/O set start/end at the playhead.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest("input, textarea, select, [contenteditable=true]")) return;
      // A dialog on top owns the keyboard: Space must press its buttons.
      if (document.querySelector("[aria-modal=true]")) return;
      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        nudge(e.shiftKey ? -5 : -1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        nudge(e.shiftKey ? 5 : 1);
      } else if (e.key === "i" || e.key === "I") {
        setEdge("start", currentTime);
      } else if (e.key === "o" || e.key === "O") {
        setEdge("end", currentTime);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const currentToken = useMemo(() => {
    for (const tok of tokens) if (tok.start <= currentTime && tok.end > currentTime) return tok;
    return null;
  }, [tokens, currentTime]);

  const caption = useMemo(() => {
    if (!currentToken) return "";
    // Show a short line of words around the current one.
    const i = tokens.indexOf(currentToken);
    return tokens
      .slice(Math.max(0, i - 3), i + 4)
      .filter((tok) => Math.abs(tok.start - currentToken.start) < 2.5)
      .map((tok) => tok.text)
      .join(" ");
  }, [tokens, currentToken]);

  const rangeText = useMemo(
    () => (transcriptLoaded ? textInRange(tokens, start, end) : active.transcript_text ?? ""),
    [transcriptLoaded, tokens, start, end, active.transcript_text],
  );

  const zoomIdx = ZOOM_LEVELS.indexOf(zoom);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-3">
      <div className="flex-1 min-h-0 grid grid-cols-[220px_minmax(0,1fr)] xl:grid-cols-[240px_minmax(0,1fr)_300px] gap-3">
        <aside className="min-h-0 flex flex-col rounded-[var(--radius-lg)] bg-[var(--color-bg-primary)] border border-[var(--color-border-light)] overflow-hidden">
          <h2 className="px-4 pt-3 pb-2 text-sm font-semibold text-[var(--color-text-primary)]">
            {t("editor.list.title")} <span className="text-[var(--color-text-muted)] font-normal">· {highlights.length}</span>
          </h2>
          <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-2 space-y-1">
            {highlights.map((h, i) => (
              <ClipRow
                key={i}
                index={i}
                highlight={h}
                active={i === activeIndex}
                selected={selectedIndices.has(i) && !processedSet.has(i)}
                processed={processedSet.has(i)}
                onActivate={() => setActiveIndex(i)}
                onToggle={() => onToggle(i)}
              />
            ))}
          </div>
        </aside>

        {/* Preview + (narrow screens) details */}
        <section className="min-h-0 flex flex-col gap-3 overflow-y-auto xl:overflow-hidden">
          <div className="relative shrink-0 xl:flex-1 xl:min-h-0 rounded-[var(--radius-lg)] bg-black border border-[var(--color-border-light)] overflow-hidden aspect-video xl:aspect-auto">
            {proxySrc ? (
              <video
                ref={videoRef}
                src={proxySrc}
                muted={muted}
                preload="auto"
                className="absolute inset-0 w-full h-full object-contain"
                onLoadedMetadata={(e) => {
                  setVideoDuration(e.currentTarget.duration || null);
                  e.currentTarget.currentTime = currentTime;
                }}
                onPlay={() => setPlaying(true)}
                onPause={() => setPlaying(false)}
                onTimeUpdate={(e) => {
                  if (e.currentTarget.paused) setCurrentTime(e.currentTarget.currentTime);
                }}
                onClick={togglePlay}
              />
            ) : (
              <ProxyStatus proxy={proxy} onRetry={retryProxy} />
            )}
            {proxySrc && caption && (
              <div className="absolute inset-x-0 bottom-[8%] flex justify-center px-6 pointer-events-none">
                <span className="max-w-[80%] text-center text-sm sm:text-base font-semibold text-white [text-shadow:0_1px_3px_rgba(0,0,0,0.9)]">
                  {caption}
                </span>
              </div>
            )}
          </div>
          <div className="xl:hidden">
            <ClipDetails
              index={activeIndex}
              highlight={active}
              start={start}
              end={end}
              locked={locked}
              rangeText={rangeText}
              padding={padding}
              sessionDir={sessionDir}
              projectTitle={projectTitle}
              onSetStart={() => setEdge("start", currentTime)}
              onSetEnd={() => setEdge("end", currentTime)}
              onNudge={(edge, d) => setEdge(edge, (edge === "start" ? start : end) + d)}
              onReset={() => {
                onReset(activeIndex);
                setAnchor(rangeOf(highlights[activeIndex]));
              }}
            />
          </div>
        </section>

        {/* Details (wide screens) */}
        <aside className="hidden xl:block min-h-0 overflow-y-auto">
          <ClipDetails
            index={activeIndex}
            highlight={active}
            start={start}
            end={end}
            locked={locked}
            rangeText={rangeText}
            padding={padding}
            sessionDir={sessionDir}
            projectTitle={projectTitle}
            onSetStart={() => setEdge("start", currentTime)}
            onSetEnd={() => setEdge("end", currentTime)}
            onNudge={(edge, d) => setEdge(edge, (edge === "start" ? start : end) + d)}
            onReset={() => {
              onReset(activeIndex);
              setAnchor(rangeOf(highlights[activeIndex]));
            }}
          />
        </aside>
      </div>

      {/* Transport + timeline */}
      <section className="shrink-0 rounded-[var(--radius-lg)] bg-[var(--color-bg-primary)] border border-[var(--color-border-light)] px-4 pt-3 pb-4">
        <div className="grid grid-cols-[1fr_auto_1fr] items-center mb-2">
          <div className="text-xs tabular-nums text-[var(--color-text-secondary)]">
            <span className="text-[var(--color-text-primary)]">{formatClock(currentTime)}</span>
            <span className="text-[var(--color-text-muted)]">
              {"  ·  "}
              {t("editor.transport.rangeSummary", {
                start: formatClock(start),
                end: formatClock(end),
                length: (end - start).toFixed(1),
              })}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <IconBtn label={t("editor.transport.previousClip")} disabled={activeIndex === 0} onClick={() => setActiveIndex(activeIndex - 1)}>
              <SkipBack className="w-4 h-4" />
            </IconBtn>
            <IconBtn label={t("editor.transport.back5")} onClick={() => nudge(-5)}>
              <RotateCcw className="w-4 h-4" />
            </IconBtn>
            <button
              type="button"
              aria-label={playing ? t("editor.transport.pause") : t("editor.transport.play")}
              title={playing ? t("editor.transport.pause") : t("editor.transport.play")}
              disabled={!proxySrc}
              onClick={togglePlay}
              className="mx-1 w-10 h-10 rounded-full bg-[var(--color-text-primary)] text-[var(--color-bg-primary)] flex items-center justify-center hover:opacity-90 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
            >
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
            </button>
            <IconBtn label={t("editor.transport.forward5")} onClick={() => nudge(5)}>
              <RotateCw className="w-4 h-4" />
            </IconBtn>
            <IconBtn
              label={t("editor.transport.nextClip")}
              disabled={activeIndex >= highlights.length - 1}
              onClick={() => setActiveIndex(activeIndex + 1)}
            >
              <SkipForward className="w-4 h-4" />
            </IconBtn>
          </div>
          <div className="flex items-center justify-end gap-1">
            <IconBtn label={t("editor.transport.zoomOut")} disabled={zoomIdx >= ZOOM_LEVELS.length - 1} onClick={() => setZoom(ZOOM_LEVELS[zoomIdx + 1])}>
              <ZoomOut className="w-4 h-4" />
            </IconBtn>
            <IconBtn label={t("editor.transport.zoomIn")} disabled={zoomIdx <= 0} onClick={() => setZoom(ZOOM_LEVELS[zoomIdx - 1])}>
              <ZoomIn className="w-4 h-4" />
            </IconBtn>
            <IconBtn label={muted ? t("editor.transport.unmute") : t("editor.transport.mute")} onClick={() => setMuted(!muted)}>
              {muted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </IconBtn>
          </div>
        </div>

        <Timeline
          viewStart={view.start}
          viewEnd={view.end}
          duration={duration}
          start={start}
          end={end}
          currentTime={currentTime}
          tokens={tokens}
          filmSrc={proxySrc}
          locked={locked}
          label={t("editor.timeline.clipLabel", { n: activeIndex + 1 })}
          onSeek={seek}
          onTrim={(s, e) => onTrim(activeIndex, s, e)}
          onTrimEnd={() => setAnchor(rangeOf(useSessionStore.getState().session!.highlights[activeIndex]))}
        />

        <p className="mt-2 text-[11px] text-[var(--color-text-muted)]">
          {locked ? t("editor.transport.hintLocked") : t("editor.transport.hint")}
        </p>
      </section>
    </div>
  );
}

function IconBtn({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="w-9 h-9 rounded-full flex items-center justify-center text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:pointer-events-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
    >
      {children}
    </button>
  );
}

function ProxyStatus({
  proxy,
  onRetry,
}: {
  proxy: EditorProps["proxy"];
  onRetry: () => void;
}) {
  const { t } = useTranslation();
  if (proxy?.status === "error") {
    return (
      <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
        <AlertTriangle aria-hidden className="w-6 h-6 text-[var(--color-error)]" />
        <p className="text-sm font-semibold text-[var(--color-text-primary)]">{t("editor.proxy.errorTitle")}</p>
        {proxy.error && (
          <p className="text-xs text-[var(--color-text-muted)] max-w-md line-clamp-3">
            {t("editor.proxy.errorReason", { reason: proxy.error })}
          </p>
        )}
        <Button size="sm" variant="outline" onClick={onRetry} className="h-9 px-4">
          {t("editor.proxy.retry")}
        </Button>
        <p className="text-xs text-[var(--color-text-muted)] max-w-sm">{t("editor.proxy.errorHint")}</p>
      </div>
    );
  }
  const pct = proxy?.percent ?? 0;
  return (
    <div role="status" className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6">
      <Loader2 aria-hidden className="w-6 h-6 animate-spin text-[var(--color-text-secondary)]" />
      <p className="text-sm text-[var(--color-text-primary)]">
        {t("editor.proxy.downloading", { percent: Math.floor(pct) })}
      </p>
      <div className="w-56 h-1.5 rounded-full bg-[var(--color-bg-hover)] overflow-hidden">
        <div className="h-full bg-[var(--color-text-secondary)] transition-all duration-300" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-[var(--color-text-muted)] max-w-sm text-center truncate">
        {proxy?.lastLog ?? t("editor.proxy.downloadingHint")}
      </p>
    </div>
  );
}

interface ClipRowProps {
  index: number;
  highlight: Highlight;
  active: boolean;
  selected: boolean;
  processed: boolean;
  onActivate: () => void;
  onToggle: () => void;
}

function ClipRow({ index, highlight, active, selected, processed, onActivate, onToggle }: ClipRowProps) {
  const { t } = useTranslation();
  const v = viralityStyle(highlight.virality_score);
  const { start, end } = rangeOf(highlight);
  const n = index + 1;
  return (
    <div
      role="button"
      tabIndex={0}
      aria-current={active ? "true" : undefined}
      onClick={onActivate}
      onKeyDown={(e) => {
        if (e.key === "Enter") onActivate();
      }}
      className={`group flex items-start gap-2 rounded-[var(--radius)] px-2.5 py-2 cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] ${
        active ? "bg-[var(--color-bg-hover)]" : "hover:bg-[var(--color-bg-card)]"
      }`}
    >
      <button
        type="button"
        aria-label={
          processed
            ? t("editor.list.alreadyRendered", { n })
            : selected
              ? t("editor.list.deselect", { n })
              : t("editor.list.select", { n })
        }
        aria-pressed={processed ? undefined : selected}
        disabled={processed}
        onClick={(e) => {
          e.stopPropagation();
          onToggle();
        }}
        className="-m-2.5 p-2.5 pt-3 shrink-0 rounded-[var(--radius-sm)] cursor-pointer disabled:cursor-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
      >
        {processed ? (
          <CheckCircle2 aria-hidden className="w-4 h-4 text-[var(--color-success)]" />
        ) : selected ? (
          <CheckSquare aria-hidden className="w-4 h-4 text-[var(--color-accent)]" />
        ) : (
          <Square aria-hidden className="w-4 h-4 text-[var(--color-text-muted)]" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <p
          className={`text-[13px] leading-snug line-clamp-2 ${
            active ? "text-[var(--color-text-primary)] font-medium" : "text-[var(--color-text-secondary)]"
          }`}
        >
          <span className="text-[var(--color-text-muted)]">{t("editor.list.clipNumber", { n })}</span> {highlight.title}
        </p>
        <div className="mt-1 flex items-center gap-2 text-xs text-[var(--color-text-muted)] tabular-nums">
          <span
            className="inline-flex items-center gap-0.5"
            style={{ color: v.color }}
            title={t("editor.list.score", { score: highlight.virality_score })}
          >
            <v.Icon aria-hidden className="w-3 h-3" />
            {highlight.virality_score}
          </span>
          <span>{t("editor.list.seconds", { n: (end - start).toFixed(0) })}</span>
          {processed && <span className="text-[var(--color-success)]">{t("editor.list.rendered")}</span>}
          {!processed && isEdited(highlight) && <span>{t("editor.list.edited")}</span>}
        </div>
      </div>
    </div>
  );
}

interface ClipDetailsProps {
  index: number;
  highlight: Highlight;
  start: number;
  end: number;
  locked: boolean;
  rangeText: string;
  padding: { leadIn: number; tailOut: number };
  sessionDir: string;
  projectTitle?: string;
  onSetStart: () => void;
  onSetEnd: () => void;
  onNudge: (edge: "start" | "end", delta: number) => void;
  onReset: () => void;
}

function ClipDetails({
  index,
  highlight,
  start,
  end,
  locked,
  rangeText,
  padding,
  sessionDir,
  projectTitle,
  onSetStart,
  onSetEnd,
  onNudge,
  onReset,
}: ClipDetailsProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const v = viralityStyle(highlight.virality_score);
  const clipPath = clipPathFor(sessionDir, index);

  return (
    <div className="rounded-[var(--radius-lg)] bg-[var(--color-bg-primary)] border border-[var(--color-border-light)] p-4 space-y-4">
      <div className="flex items-start gap-2">
        <h2 className="flex-1 text-sm font-semibold text-[var(--color-text-primary)] leading-snug">
          <span className="text-[var(--color-text-muted)]">{t("editor.list.clipNumber", { n: index + 1 })}</span>{" "}
          {highlight.title}
        </h2>
        <span
          className="inline-flex items-center gap-1 text-xs font-semibold shrink-0 tabular-nums"
          style={{ color: v.color }}
          title={t("editor.list.score", { score: highlight.virality_score })}
        >
          <v.Icon aria-hidden className="w-3 h-3" />
          {t("editor.details.scoreBadge", { score: highlight.virality_score })}
        </span>
      </div>

      {highlight.hook_text && (
        <div className="flex items-start gap-2 text-sm">
          <Quote aria-hidden className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-text-muted)]" />
          <span className="text-[var(--color-text-primary)]">{highlight.hook_text}</span>
        </div>
      )}

      <div className="rounded-[var(--radius)] bg-[var(--color-bg-card)] p-3 space-y-2">
        <EdgeRow
          edge="start"
          value={start}
          locked={locked}
          onMinus={() => onNudge("start", -0.5)}
          onPlus={() => onNudge("start", 0.5)}
          onHere={onSetStart}
        />
        <EdgeRow
          edge="end"
          value={end}
          locked={locked}
          onMinus={() => onNudge("end", -0.5)}
          onPlus={() => onNudge("end", 0.5)}
          onHere={onSetEnd}
        />
        <div className="flex items-center justify-between gap-2 pt-1 text-xs text-[var(--color-text-muted)]">
          <span>{t("editor.details.padding", { leadIn: padding.leadIn, tailOut: padding.tailOut })}</span>
          {isEdited(highlight) && !locked && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex min-h-9 shrink-0 items-center gap-1 rounded-[var(--radius-sm)] px-1 text-[var(--color-accent)] hover:underline cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
            >
              <Undo2 aria-hidden className="w-3 h-3" /> {t("editor.details.reset")}
            </button>
          )}
        </div>
      </div>

      {highlight.description && (
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{highlight.description}</p>
      )}

      <div>
        <h3 className="text-xs font-medium text-[var(--color-text-secondary)] mb-1">{t("editor.details.transcriptTitle")}</h3>
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed max-h-40 overflow-y-auto">
          {rangeText || <span className="text-[var(--color-text-muted)]">{t("editor.details.transcriptEmpty")}</span>}
        </p>
      </div>

      {locked && (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-9 gap-1.5"
            onClick={() =>
              navigate("/clip", {
                state: {
                  clipPath,
                  title: highlight.title,
                  hookText: highlight.hook_text,
                  description: highlight.description,
                  startTime: highlight.start_time.split(",")[0],
                  endTime: highlight.end_time.split(",")[0],
                  sessionDir,
                  highlightIndex: index,
                  projectTitle,
                },
              })
            }
          >
            <Play aria-hidden className="w-3.5 h-3.5" /> {t("editor.details.viewClip")}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-9 gap-1.5"
            onClick={() => invoke("open_path_in_explorer", { path: clipPath }).catch(console.error)}
          >
            <FolderOpen aria-hidden className="w-3.5 h-3.5" /> {t("editor.details.openFolder")}
          </Button>
        </div>
      )}
    </div>
  );
}

function EdgeRow({
  edge,
  value,
  locked,
  onMinus,
  onPlus,
  onHere,
}: {
  edge: "start" | "end";
  value: number;
  locked: boolean;
  onMinus: () => void;
  onPlus: () => void;
  onHere: () => void;
}) {
  const { t } = useTranslation();
  const label = edge === "start" ? t("editor.details.start") : t("editor.details.end");
  const edgeWord = edge === "start" ? t("editor.details.edgeStart") : t("editor.details.edgeEnd");
  const hereTitle = edge === "start" ? t("editor.details.hereTitleStart") : t("editor.details.hereTitleEnd");
  const minusLabel = t("editor.details.minus", { edge: edgeWord });
  const plusLabel = t("editor.details.plus", { edge: edgeWord });
  const btn =
    "h-9 px-2 rounded-[var(--radius-sm)] text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:pointer-events-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]";
  return (
    <div className="flex items-center gap-1">
      <span className="w-12 text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className="flex-1 text-sm tabular-nums text-[var(--color-text-primary)]">{formatClock(value)}</span>
      <button type="button" className={btn} disabled={locked} onClick={onMinus} aria-label={minusLabel} title={minusLabel}>
        −0.5
      </button>
      <button type="button" className={btn} disabled={locked} onClick={onPlus} aria-label={plusLabel} title={plusLabel}>
        +0.5
      </button>
      <button type="button" className={btn} disabled={locked} onClick={onHere} title={hereTitle}>
        {t("editor.details.here")}
      </button>
    </div>
  );
}
