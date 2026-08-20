import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckSquare,
  Square,
  Flame,
  Zap,
  Sparkle,
  Clock,
  Quote,
  MessageSquareText,
  Film,
  FolderOpen,
  Play,
} from "lucide-react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useSessionStore } from "@/stores/sessionStore";
import type { Highlight } from "@/hooks/highlights";
import { ProcessConfirmDialog } from "@/components/ProcessConfirmDialog";

function viralityStyle(score: number) {
  if (score >= 7) {
    return {
      label: "High",
      color: "var(--color-success)",
      bg: "var(--color-success-bg)",
      Icon: Flame,
    };
  }
  if (score >= 5) {
    return {
      label: "Medium",
      color: "var(--color-warning)",
      bg: "var(--color-warning-bg)",
      Icon: Zap,
    };
  }
  return {
    label: "Low",
    color: "var(--color-error)",
    bg: "var(--color-error-bg)",
    Icon: Sparkle,
  };
}

function stripMs(ts: string): string {
  return ts.split(",")[0];
}

export function HighlightSelectionPage() {
  const navigate = useNavigate();
  const { session, origin, selectedIndices, toggleSelected, selectAll, deselectAll, getSelectedHighlights } =
    useSessionStore();

  const [showProcessDialog, setShowProcessDialog] = useState(false);

  useEffect(() => {
    if (!session) navigate("/");
  }, [session, navigate]);

  if (!session) return null;

  const backTo = origin === "library" ? "/library" : "/";
  const backLabel = origin === "library" ? "Back to Library" : "Back to Create";

  const highlights = session.highlights;
  const processedSet = new Set(session.processed_highlights ?? []);
  // Only count unprocessed selected highlights
  const selectedCount = [...selectedIndices].filter((i) => !processedSet.has(i)).length;

  return (
    <div className="space-y-5">
      <Button
        variant="ghost"
        onClick={() => navigate(backTo)}
        className="gap-2 text-[var(--color-text-secondary)]"
      >
        <ArrowLeft className="w-4 h-4" />
        {backLabel}
      </Button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">
            Select Highlights
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            {highlights.length} viral moments found in{" "}
            <span className="text-[var(--color-text-secondary)]">
              {session.video_info.title || "the video"}
            </span>
          </p>
        </div>
      </div>

      {/* Legend + bulk actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1">
            <Flame className="w-3.5 h-3.5 text-[var(--color-success)]" /> 7-10 High
          </span>
          <span className="flex items-center gap-1">
            <Zap className="w-3.5 h-3.5 text-[var(--color-warning)]" /> 5-6 Medium
          </span>
          <span className="flex items-center gap-1">
            <Sparkle className="w-3.5 h-3.5 text-[var(--color-error)]" /> 1-4 Low
          </span>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={selectAll} className="gap-1.5">
            <CheckSquare className="w-3.5 h-3.5" /> Select all
          </Button>
          <Button variant="outline" size="sm" onClick={deselectAll} className="gap-1.5">
            <Square className="w-3.5 h-3.5" /> Clear
          </Button>
        </div>
      </div>

      {/* Highlight cards */}
      <div className="space-y-3">
        {highlights.map((h, i) => (
          <HighlightCard
            key={i}
            index={i}
            highlight={h}
            selected={selectedIndices.has(i) && !processedSet.has(i)}
            processed={processedSet.has(i)}
            sessionDir={session.session_dir}
            onToggle={() => { if (!processedSet.has(i)) toggleSelected(i); }}
          />
        ))}
      </div>

      {/* Sticky action bar */}
      <div className="sticky bottom-0 -mx-6 px-6 py-4 bg-gradient-to-t from-[var(--color-bg-secondary)] via-[var(--color-bg-secondary)] to-transparent">
        <Button
          size="lg"
          disabled={selectedCount === 0}
          onClick={() => setShowProcessDialog(true)}
          className="w-full h-13 gap-2 shadow-[var(--shadow)]"
        >
          <Film className="w-5 h-5" />
          Process {selectedCount} clip{selectedCount === 1 ? "" : "s"}
        </Button>
      </div>

      {/* Process confirmation modal */}
      {showProcessDialog && (
        <ProcessConfirmDialog
          clipCount={selectedCount}
          captionsAvailable={session.caption_available ?? true}
          onConfirm={(options) => {
            setShowProcessDialog(false);
            const selected = getSelectedHighlights();
            // Attach original highlight index for dedup tracking
            const highlightsWithIndex = selected.map((h) => {
              const originalIndex = highlights.indexOf(h);
              return { ...h, _highlight_index: originalIndex };
            });
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

interface HighlightCardProps {
  index: number;
  highlight: Highlight;
  selected: boolean;
  processed: boolean;
  sessionDir: string;
  onToggle: () => void;
}

function HighlightCard({ index, highlight, selected, processed, sessionDir, onToggle }: HighlightCardProps) {
  const navigate = useNavigate();
  const v = viralityStyle(highlight.virality_score);

  const clipPath = `${sessionDir}\\clips\\clip_${String(index).padStart(3, "0")}\\master.mp4`;

  const handleOpenClip = (e: React.MouseEvent) => {
    e.stopPropagation();
    invoke("open_path_in_explorer", { path: clipPath }).catch(console.error);
  };

  const handleViewClip = (e: React.MouseEvent) => {
    e.stopPropagation();
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
    });
  };

  return (
    <Card
      className={`p-0 overflow-hidden transition-all duration-200 ${
        processed
          ? "border-[var(--color-success)]/30 bg-[var(--color-success-bg)]/20"
          : selected
          ? "border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]/30 cursor-pointer"
          : "hover:border-[var(--color-border)] cursor-pointer"
      }`}
      onClick={processed ? undefined : onToggle}
    >
      <div className="flex">
        {/* Selection indicator strip */}
        <div
          className={`w-1 shrink-0 transition-colors ${
            selected ? "bg-[var(--color-accent)]" : "bg-transparent"
          }`}
        />

        <div className="flex-1 p-4 space-y-3">
          {/* Top row */}
          <div className="flex items-start gap-3">
            <div className="pt-0.5">
              {processed ? (
                <CheckSquare className="w-5 h-5 text-[var(--color-success)]" />
              ) : selected ? (
                <CheckSquare className="w-5 h-5 text-[var(--color-accent)]" />
              ) : (
                <Square className="w-5 h-5 text-[var(--color-text-muted)]" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-[var(--color-text-primary)] leading-snug">
                <span className="text-[var(--color-text-muted)]">#{index + 1}</span>{" "}
                {highlight.title}
              </p>
            </div>

            {/* Virality badge */}
            <span
              className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full shrink-0"
              style={{ color: v.color, backgroundColor: v.bg }}
            >
              <v.Icon className="w-3.5 h-3.5" />
              {highlight.virality_score}/10
            </span>
          </div>

          {/* Hook */}
          {highlight.hook_text && (
            <div className="flex items-start gap-2 text-sm">
              <Quote className="w-4 h-4 shrink-0 mt-0.5 text-[var(--color-accent)]" />
              <span className="font-medium text-[var(--color-text-primary)]">
                {highlight.hook_text}
              </span>
            </div>
          )}

          {/* Description */}
          {highlight.description && (
            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
              {highlight.description}
            </p>
          )}

          {/* Transcript preview */}
          {highlight.transcript_text && (
            <div className="rounded-[var(--radius-sm)] bg-[var(--color-bg-secondary)] p-3">
              <div className="flex items-center gap-1.5 mb-1 text-xs font-medium text-[var(--color-text-muted)]">
                <MessageSquareText className="w-3.5 h-3.5" />
                Transcript
              </div>
              <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed line-clamp-3">
                {highlight.transcript_text}
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
            <Clock className="w-3.5 h-3.5" />
            {stripMs(highlight.start_time)} → {stripMs(highlight.end_time)}
            <span className="text-[var(--color-text-secondary)]">
              ({Math.round(highlight.duration_seconds)}s)
            </span>
            {processed && (
              <span className="ml-auto flex items-center gap-2">
                <span className="flex items-center gap-1 text-[var(--color-success)]">
                  <Film className="w-3.5 h-3.5" />
                  Clip ready
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleViewClip}
                  className="h-6 px-2 gap-1 text-xs text-[var(--color-accent)]"
                >
                  <Play className="w-3.5 h-3.5" />
                  View
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleOpenClip}
                  className="h-6 px-2 gap-1 text-xs text-[var(--color-text-muted)]"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                </Button>
              </span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
