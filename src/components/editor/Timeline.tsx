import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatRuler } from "@/lib/timecode";
import type { TimedToken } from "@/hooks/transcript";
import { useFilmstrip } from "./useFilmstrip";

/** Shortest clip the handles allow, in seconds. */
export const MIN_CLIP_SECONDS = 1;
const SNAP_PX = 6;
const TRACK_H = 52;

type DragMode = "start" | "end" | "move" | "seek";

interface TimelineProps {
  viewStart: number;
  viewEnd: number;
  duration: number;
  start: number;
  end: number;
  currentTime: number;
  tokens: TimedToken[];
  filmSrc: string | null;
  locked: boolean;
  label: string;
  onSeek: (t: number) => void;
  onTrim: (start: number, end: number) => void;
  /** Fired once a handle drag is released, so the view can re-center. */
  onTrimEnd: () => void;
}

const RULER_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800];

export function Timeline({
  viewStart,
  viewEnd,
  duration,
  start,
  end,
  currentTime,
  tokens,
  filmSrc,
  locked,
  label,
  onSeek,
  onTrim,
  onTrimEnd,
}: TimelineProps) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);
  const drag = useRef<{ mode: DragMode; grabOffset: number } | null>(null);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const span = Math.max(0.001, viewEnd - viewStart);
  const toX = (t: number) => ((t - viewStart) / span) * width;
  const toPct = (t: number) => ((t - viewStart) / span) * 100;

  const filmCanvasRef = useFilmstrip(filmSrc, viewStart, viewEnd, width, TRACK_H);

  const ticks = useMemo(() => {
    const step = RULER_STEPS.find((s) => span / s <= 9) ?? RULER_STEPS[RULER_STEPS.length - 1];
    const first = Math.ceil(viewStart / step) * step;
    const out: number[] = [];
    for (let t = first; t <= viewEnd + 1e-6; t += step) out.push(t);
    return out;
  }, [viewStart, viewEnd, span]);

  const timeAt = (clientX: number) => {
    const rect = trackRef.current!.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return viewStart + ratio * span;
  };

  const snap = (t: number, edge: "start" | "end", altKey: boolean) => {
    if (altKey || width === 0) return t;
    let best = t;
    let bestPx = SNAP_PX;
    for (const tok of tokens) {
      const cand = edge === "start" ? tok.start : tok.end;
      if (cand < viewStart || cand > viewEnd) continue;
      const px = Math.abs(toX(cand) - toX(t));
      if (px < bestPx) {
        bestPx = px;
        best = cand;
      }
    }
    return best;
  };

  const clampRange = (s: number, e: number) => {
    const lo = 0;
    const hi = duration;
    return [Math.max(lo, s), Math.min(hi, e)] as const;
  };

  const apply = (clientX: number, altKey: boolean) => {
    const d = drag.current;
    if (!d) return;
    const t = timeAt(clientX);
    if (d.mode === "seek") {
      onSeek(t);
      return;
    }
    if (d.mode === "start") {
      const s = Math.min(snap(t, "start", altKey), end - MIN_CLIP_SECONDS);
      const [cs] = clampRange(s, end);
      onTrim(cs, end);
      onSeek(cs);
    } else if (d.mode === "end") {
      const e = Math.max(snap(t, "end", altKey), start + MIN_CLIP_SECONDS);
      const [, ce] = clampRange(start, e);
      onTrim(start, ce);
      onSeek(ce);
    } else {
      const len = end - start;
      let s = t - d.grabOffset;
      s = Math.max(0, Math.min(s, duration - len));
      onTrim(s, s + len);
      onSeek(s);
    }
  };

  const begin = (mode: DragMode) => (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    if (locked && mode !== "seek") mode = "seek";
    e.stopPropagation();
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    drag.current = { mode, grabOffset: mode === "move" ? timeAt(e.clientX) - start : 0 };
    if (mode === "seek") apply(e.clientX, e.altKey);
  };

  const move = (e: React.PointerEvent) => {
    if (drag.current) apply(e.clientX, e.altKey);
  };

  const finish = (e: React.PointerEvent) => {
    const d = drag.current;
    drag.current = null;
    (e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);
    if (d && d.mode !== "seek") onTrimEnd();
  };

  const selLeft = toPct(start);
  const selWidth = toPct(end) - selLeft;
  const playheadPct = toPct(currentTime);
  const handleProps = { onPointerMove: move, onPointerUp: finish, onPointerCancel: finish };

  return (
    <div className="select-none">
      {/* Ruler */}
      <div
        className="relative h-6 cursor-pointer"
        onPointerDown={begin("seek")}
        {...handleProps}
      >
        {ticks.map((t) => (
          <span
            key={t}
            className="absolute top-0 -translate-x-1/2 text-[11px] tabular-nums text-[var(--color-text-muted)]"
            style={{ left: `${toPct(t)}%` }}
          >
            {formatRuler(t)}
          </span>
        ))}
      </div>

      {/* Track */}
      <div
        ref={trackRef}
        className="relative rounded-[var(--radius-sm)] overflow-hidden cursor-pointer"
        style={{ height: TRACK_H }}
        onPointerDown={begin("seek")}
        {...handleProps}
      >
        <canvas
          ref={filmCanvasRef}
          className="absolute inset-0 w-full h-full pointer-events-none"
        />
        {/* Dim everything outside the selection */}
        <div
          className="absolute inset-y-0 left-0 bg-black/65 pointer-events-none"
          style={{ width: `${Math.max(0, selLeft)}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 bg-black/65 pointer-events-none"
          style={{ width: `${Math.max(0, 100 - selLeft - selWidth)}%` }}
        />

        {/* Selection */}
        <div
          className={`absolute inset-y-0 rounded-[var(--radius-sm)] border-2 ${
            locked ? "border-[var(--color-success)] cursor-pointer" : "border-white cursor-grab active:cursor-grabbing"
          }`}
          style={{ left: `${selLeft}%`, width: `${selWidth}%` }}
          onPointerDown={begin(locked ? "seek" : "move")}
          {...handleProps}
        >
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-white drop-shadow pointer-events-none truncate max-w-[calc(100%-24px)]">
            {label}
          </span>
          {!locked && (
            <>
              <Handle side="left" onPointerDown={begin("start")} {...handleProps} />
              <Handle side="right" onPointerDown={begin("end")} {...handleProps} />
            </>
          )}
        </div>

        {/* Playhead */}
        {playheadPct >= 0 && playheadPct <= 100 && (
          <div
            className="absolute inset-y-0 w-0.5 bg-[var(--color-warning)] pointer-events-none"
            style={{ left: `${playheadPct}%` }}
          >
            <div className="absolute -top-0.5 -left-[5px] w-3 h-3 rounded-full bg-[var(--color-warning)]" />
          </div>
        )}
      </div>
    </div>
  );
}

function Handle({
  side,
  ...events
}: {
  side: "left" | "right";
  onPointerDown: (e: React.PointerEvent) => void;
  onPointerMove: (e: React.PointerEvent) => void;
  onPointerUp: (e: React.PointerEvent) => void;
  onPointerCancel: (e: React.PointerEvent) => void;
}) {
  const { t } = useTranslation();
  return (
    <div
      role="slider"
      aria-label={side === "left" ? t("editor.timeline.handleStart") : t("editor.timeline.handleEnd")}
      className={`absolute inset-y-0 w-3 flex items-center justify-center bg-white cursor-ew-resize ${
        side === "left" ? "-left-[2px] rounded-l-[var(--radius-sm)]" : "-right-[2px] rounded-r-[var(--radius-sm)]"
      }`}
      {...events}
    >
      <span className="w-0.5 h-4 rounded-full bg-black/60" />
    </div>
  );
}
