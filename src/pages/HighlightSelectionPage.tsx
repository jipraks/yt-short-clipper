import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  if (score >= 7) return { color: "var(--color-success)", bg: "var(--color-success-bg)", Icon: Flame };
  if (score >= 5) return { color: "var(--color-warning)", bg: "var(--color-warning-bg)", Icon: Zap };
  return { color: "var(--color-error)", bg: "var(--color-error-bg)", Icon: Sparkle };
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

  const highlights = session.highlights;
  const processedSet = new Set(session.processed_highlights ?? []);
  const selectedCount = [...selectedIndices].filter((i) => !processedSet.has(i)).length;
  const safeIndex = Math.min(activeIndex, highlights.length - 1);
  const backTo = origin === "library" ? "/library" : "/";

  return (
    <div className="h-full flex flex-col gap-3 p-4 min-h-0">
      {/* Header */}
      <header className="flex items-center gap-3 shrink-0">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate(backTo)}
          className="gap-1.5 text-[var(--color-text-secondary)] shrink-0"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </Button>
        <span className="text-[var(--color-text-muted)]">/</span>
        <h1 className="flex-1 min-w-0 truncate text-sm font-semibold text-[var(--color-text-primary)]">
          {session.video_info.title || "Select Highlights"}
        </h1>
        <Button variant="outline" size="sm" onClick={selectAll} className="gap-1.5 shrink-0">
          <CheckSquare className="w-3.5 h-3.5" /> All
        </Button>
        <Button variant="outline" size="sm" onClick={deselectAll} className="gap-1.5 shrink-0">
          <Square className="w-3.5 h-3.5" /> Clear
        </Button>
        <Button
          size="sm"
          disabled={selectedCount === 0}
          onClick={() => setShowProcessDialog(true)}
          className="gap-1.5 shrink-0 rounded-full px-4"
        >
          <Film className="w-4 h-4" />
          Process {selectedCount} clip{selectedCount === 1 ? "" : "s"}
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
  proxy,
  retryProxy,
  tokens,
  transcriptLoaded,
  padding,
  onToggle,
  onTrim,
  onReset,
}: EditorProps) {
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

  const seek = useCallback((t: number) => {
    const v = videoRef.current;
    setCurrentTime(t);
    if (v && v.readyState >= 1) v.currentTime = t;
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

  const setEdge = (edge: "start" | "end", t: number) => {
    if (locked) return;
    if (edge === "start") onTrim(activeIndex, Math.max(0, Math.min(t, end - MIN_CLIP_SECONDS)), end);
    else onTrim(activeIndex, start, Math.min(duration, Math.max(t, start + MIN_CLIP_SECONDS)));
  };

  // Keyboard: Space play, arrows seek, I/O set start/end at the playhead.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest("input, textarea, select, [contenteditable=true]")) return;
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
    for (const t of tokens) if (t.start <= currentTime && t.end > currentTime) return t;
    return null;
  }, [tokens, currentTime]);

  const caption = useMemo(() => {
    if (!currentToken) return "";
    // Show a short line of words around the current one.
    const i = tokens.indexOf(currentToken);
    return tokens
      .slice(Math.max(0, i - 3), i + 4)
      .filter((t) => Math.abs(t.start - currentToken.start) < 2.5)
      .map((t) => t.text)
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
        {/* Clip list */}
        <aside className="min-h-0 flex flex-col rounded-[var(--radius-lg)] bg-[var(--color-bg-primary)] border border-[var(--color-border-light)] overflow-hidden">
          <div className="px-4 pt-3 pb-2 text-sm font-semibold text-[var(--color-text-primary)]">
            AI Clips <span className="text-[var(--color-text-muted)] font-normal">· {highlights.length}</span>
          </div>
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
              {formatClock(start)} – {formatClock(end)} ({(end - start).toFixed(1)}s)
            </span>
          </div>
          <div className="flex items-center gap-1">
            <IconBtn label="Previous clip" disabled={activeIndex === 0} onClick={() => setActiveIndex(activeIndex - 1)}>
              <SkipBack className="w-4 h-4" />
            </IconBtn>
            <IconBtn label="Back 5 seconds" onClick={() => nudge(-5)}>
              <RotateCcw className="w-4 h-4" />
            </IconBtn>
            <button
              type="button"
              aria-label={playing ? "Pause" : "Play clip"}
              disabled={!proxySrc}
              onClick={togglePlay}
              className="mx-1 w-10 h-10 rounded-full bg-[var(--color-accent-fill)] text-[var(--color-text-on-accent)] flex items-center justify-center hover:bg-[var(--color-accent-hover)] disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            >
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
            </button>
            <IconBtn label="Forward 5 seconds" onClick={() => nudge(5)}>
              <RotateCw className="w-4 h-4" />
            </IconBtn>
            <IconBtn
              label="Next clip"
              disabled={activeIndex >= highlights.length - 1}
              onClick={() => setActiveIndex(activeIndex + 1)}
            >
              <SkipForward className="w-4 h-4" />
            </IconBtn>
          </div>
          <div className="flex items-center justify-end gap-1">
            <IconBtn label="Zoom out" disabled={zoomIdx >= ZOOM_LEVELS.length - 1} onClick={() => setZoom(ZOOM_LEVELS[zoomIdx + 1])}>
              <ZoomOut className="w-4 h-4" />
            </IconBtn>
            <IconBtn label="Zoom in" disabled={zoomIdx <= 0} onClick={() => setZoom(ZOOM_LEVELS[zoomIdx - 1])}>
              <ZoomIn className="w-4 h-4" />
            </IconBtn>
            <IconBtn label={muted ? "Unmute" : "Mute"} onClick={() => setMuted(!muted)}>
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
          label={`Clip ${activeIndex + 1}`}
          onSeek={seek}
          onTrim={(s, e) => onTrim(activeIndex, s, e)}
          onTrimEnd={() => setAnchor(rangeOf(useSessionStore.getState().session!.highlights[activeIndex]))}
        />

        <p className="mt-2 text-[11px] text-[var(--color-text-muted)]">
          {locked
            ? "This clip is already rendered, so its range is locked."
            : "Drag the white handles to trim, or drag the clip to move it. Handles snap to word edges; hold Alt to move freely. Keys: Space play · ←/→ seek · I/O set start/end."}
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
      className="w-8 h-8 rounded-full flex items-center justify-center text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
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
  if (proxy?.status === "error") {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
        <AlertTriangle className="w-6 h-6 text-[var(--color-error)]" />
        <p className="text-sm text-[var(--color-text-primary)]">Preview video could not be downloaded.</p>
        <p className="text-xs text-[var(--color-text-muted)] max-w-md line-clamp-3">{proxy.error}</p>
        <Button size="sm" variant="outline" onClick={onRetry}>
          Try again
        </Button>
        <p className="text-[11px] text-[var(--color-text-muted)]">
          You can still trim on the timeline and process clips without the preview.
        </p>
      </div>
    );
  }
  const pct = proxy?.percent ?? 0;
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6">
      <Loader2 className="w-6 h-6 animate-spin text-[var(--color-text-secondary)]" />
      <p className="text-sm text-[var(--color-text-primary)]">Downloading preview video… {Math.floor(pct)}%</p>
      <div className="w-56 h-1.5 rounded-full bg-[var(--color-bg-hover)] overflow-hidden">
        <div className="h-full bg-[var(--color-accent)] transition-all duration-300" style={{ width: `${pct}%` }} />
      </div>
      <p className="text-[11px] text-[var(--color-text-muted)] max-w-sm text-center truncate">
        {proxy?.lastLog ?? "A 360p copy of the whole video, used only for previewing."}
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
  const v = viralityStyle(highlight.virality_score);
  const { start, end } = rangeOf(highlight);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onActivate}
      onKeyDown={(e) => {
        if (e.key === "Enter") onActivate();
      }}
      className={`group flex items-start gap-2 rounded-[var(--radius)] px-2.5 py-2 cursor-pointer transition-colors ${
        active ? "bg-[var(--color-bg-hover)]" : "hover:bg-[var(--color-bg-card)]"
      }`}
    >
      <button
        type="button"
        aria-label={processed ? "Already rendered" : selected ? "Deselect clip" : "Select clip"}
        disabled={processed}
        onClick={(e) => {
          e.stopPropagation();
          onToggle();
        }}
        className="pt-0.5 shrink-0 cursor-pointer disabled:cursor-default"
      >
        {processed ? (
          <CheckCircle2 className="w-4 h-4 text-[var(--color-success)]" />
        ) : selected ? (
          <CheckSquare className="w-4 h-4 text-[var(--color-accent)]" />
        ) : (
          <Square className="w-4 h-4 text-[var(--color-text-muted)]" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <p
          className={`text-[13px] leading-snug line-clamp-2 ${
            active ? "text-[var(--color-text-primary)] font-medium" : "text-[var(--color-text-secondary)]"
          }`}
        >
          <span className="text-[var(--color-text-muted)]">#{index + 1}</span> {highlight.title}
        </p>
        <div className="mt-1 flex items-center gap-2 text-[11px] text-[var(--color-text-muted)] tabular-nums">
          <span className="inline-flex items-center gap-0.5" style={{ color: v.color }}>
            <v.Icon className="w-3 h-3" />
            {highlight.virality_score}
          </span>
          <span>{(end - start).toFixed(0)}s</span>
          {processed && <span className="text-[var(--color-success)]">Ready</span>}
          {!processed && isEdited(highlight) && <span className="text-[var(--color-warning)]">Edited</span>}
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
  onSetStart,
  onSetEnd,
  onNudge,
  onReset,
}: ClipDetailsProps) {
  const navigate = useNavigate();
  const v = viralityStyle(highlight.virality_score);
  const clipPath = clipPathFor(sessionDir, index);

  return (
    <div className="rounded-[var(--radius-lg)] bg-[var(--color-bg-primary)] border border-[var(--color-border-light)] p-4 space-y-4">
      <div className="flex items-start gap-2">
        <p className="flex-1 text-sm font-semibold text-[var(--color-text-primary)] leading-snug">
          <span className="text-[var(--color-text-muted)]">#{index + 1}</span> {highlight.title}
        </p>
        <span
          className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full shrink-0"
          style={{ color: v.color, backgroundColor: v.bg }}
        >
          <v.Icon className="w-3 h-3" />
          {highlight.virality_score}/10
        </span>
      </div>

      {highlight.hook_text && (
        <div className="flex items-start gap-2 text-sm">
          <Quote className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-text-muted)]" />
          <span className="text-[var(--color-text-primary)]">{highlight.hook_text}</span>
        </div>
      )}

      {/* Range controls */}
      <div className="rounded-[var(--radius)] bg-[var(--color-bg-card)] p-3 space-y-2">
        <EdgeRow
          label="Start"
          value={start}
          locked={locked}
          onMinus={() => onNudge("start", -0.5)}
          onPlus={() => onNudge("start", 0.5)}
          onHere={onSetStart}
        />
        <EdgeRow
          label="End"
          value={end}
          locked={locked}
          onMinus={() => onNudge("end", -0.5)}
          onPlus={() => onNudge("end", 0.5)}
          onHere={onSetEnd}
        />
        <div className="flex items-center justify-between pt-1 text-[11px] text-[var(--color-text-muted)]">
          <span>
            Render adds {padding.leadIn}s before and {padding.tailOut}s after
          </span>
          {isEdited(highlight) && !locked && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer"
            >
              <Undo2 className="w-3 h-3" /> Reset to AI
            </button>
          )}
        </div>
      </div>

      {highlight.description && (
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">{highlight.description}</p>
      )}

      <div>
        <p className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Transcript in range</p>
        <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed max-h-40 overflow-y-auto">
          {rangeText || "No transcript for this range."}
        </p>
      </div>

      {locked && (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
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
                },
              })
            }
          >
            <Play className="w-3.5 h-3.5" /> View clip
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5"
            onClick={() => invoke("open_path_in_explorer", { path: clipPath }).catch(console.error)}
          >
            <FolderOpen className="w-3.5 h-3.5" /> Open folder
          </Button>
        </div>
      )}
    </div>
  );
}

function EdgeRow({
  label,
  value,
  locked,
  onMinus,
  onPlus,
  onHere,
}: {
  label: string;
  value: number;
  locked: boolean;
  onMinus: () => void;
  onPlus: () => void;
  onHere: () => void;
}) {
  const btn =
    "h-7 px-2 rounded-[var(--radius-sm)] text-xs text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:pointer-events-none cursor-pointer";
  return (
    <div className="flex items-center gap-1">
      <span className="w-10 text-xs text-[var(--color-text-muted)]">{label}</span>
      <span className="flex-1 text-sm tabular-nums text-[var(--color-text-primary)]">{formatClock(value)}</span>
      <button type="button" className={btn} disabled={locked} onClick={onMinus} title="−0.5s">
        −0.5
      </button>
      <button type="button" className={btn} disabled={locked} onClick={onPlus} title="+0.5s">
        +0.5
      </button>
      <button type="button" className={btn} disabled={locked} onClick={onHere} title={`Set ${label.toLowerCase()} at the playhead`}>
        Here
      </button>
    </div>
  );
}
