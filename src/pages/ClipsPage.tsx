import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { convertFileSrc } from "@tauri-apps/api/core";
import { ArrowRight, Film, Loader2, RefreshCw, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { formatSessionId, listClips, type ClipSummary } from "@/hooks/sessions";
import { useOpenSession } from "@/hooks/useOpenSession";
import { cn } from "@/lib/utils";

/** "0:32" or "1:05", for a clip's length. */
function duration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/**
 * Every finished clip in one place. Each card names the session it came from
 * and links back to it; ?session=<id> narrows the page to one session, which
 * is where a project's "See clips" link lands.
 */
export function ClipsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const sessionFilter = params.get("session");
  const [clips, setClips] = useState<ClipSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const { open: openSession, openingDir } = useOpenSession();

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setClips(await listClips());
    } catch (err) {
      console.error("Failed to list clips", err);
      toast.error(t("clipsPage.loadFailed"));
      setClips((prev) => prev ?? []);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const shown = useMemo(() => {
    if (!clips) return [];
    if (!sessionFilter) return clips;
    // One session reads best in the order its highlights were found.
    return clips.filter((c) => c.sessionId === sessionFilter).sort((a, b) => a.highlightIndex - b.highlightIndex);
  }, [clips, sessionFilter]);

  const openClip = (clip: ClipSummary) =>
    navigate("/clip", {
      state: {
        clipPath: clip.clipPath,
        title: clip.title,
        hookText: clip.hookText,
        description: clip.description,
        startTime: clip.startTime.split(",")[0],
        endTime: clip.endTime.split(",")[0],
        sessionDir: clip.sessionDir,
        highlightIndex: clip.highlightIndex,
        projectTitle: clip.sessionTitle,
      },
    });

  return (
    <div className="mx-auto max-w-6xl py-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{t("clipsPage.title")}</h1>
          <p className="mt-1 max-w-xl text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("clipsPage.subtitle")}</p>
        </div>
        <Button variant="outline" onClick={() => void refresh()} disabled={loading} className="h-10 gap-2">
          {loading ? <Loader2 aria-hidden className="h-4 w-4 animate-spin" /> : <RefreshCw aria-hidden className="h-4 w-4" />}
          {t("library.refresh")}
        </Button>
      </div>

      {sessionFilter && (
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="text-sm text-[var(--color-text-secondary)]">
            {t("clipsPage.filtered", { id: formatSessionId(sessionFilter) })}
          </span>
          <button
            type="button"
            onClick={() => setParams({})}
            className="inline-flex h-8 items-center gap-1.5 rounded-full border border-[var(--color-border)] px-3 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            <X aria-hidden className="h-3.5 w-3.5" />
            {t("clipsPage.showAll")}
          </button>
        </div>
      )}

      {clips === null ? (
        <p className="mt-16 flex items-center justify-center gap-2 text-sm text-[var(--color-text-muted)]">
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          {t("clipsPage.loading")}
        </p>
      ) : shown.length === 0 ? (
        sessionFilter ? (
          <p className="mt-12 text-center text-sm text-[var(--color-text-muted)]">{t("clipsPage.emptyFiltered")}</p>
        ) : (
          <EmptyState onAction={() => navigate("/library")} />
        )
      ) : (
        <>
          <p className="mt-6 text-xs font-medium text-[var(--color-text-muted)]">{t("clipsPage.count", { count: shown.length })}</p>
          <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {shown.map((clip) => (
              <ClipCard
                key={clip.clipPath}
                clip={clip}
                onOpen={() => openClip(clip)}
                onOpenSession={() => void openSession(clip.sessionDir)}
                openingSession={openingDir === clip.sessionDir}
              />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function ClipCard({
  clip,
  onOpen,
  onOpenSession,
  openingSession,
}: {
  clip: ClipSummary;
  onOpen: () => void;
  onOpenSession: () => void;
  openingSession: boolean;
}) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const id = formatSessionId(clip.sessionId);
  const wide = clip.reframeMode === "original";
  const mode = clip.reframeMode as "face" | "centered" | "original";
  const shape = mode === "face" || mode === "centered" || mode === "original" ? t(`clipsPage.shape.${mode}`) : null;

  // Hovering plays a silent preview; leaving puts it back on its first frame.
  const preview = (play: boolean) => {
    const v = videoRef.current;
    if (!v) return;
    if (play) void v.play().catch(() => {});
    else {
      v.pause();
      v.currentTime = 0.5;
    }
  };

  return (
    <li className="min-w-0">
      <button
        type="button"
        onClick={onOpen}
        onMouseEnter={() => preview(true)}
        onMouseLeave={() => preview(false)}
        onFocus={() => preview(true)}
        onBlur={() => preview(false)}
        className="group block w-full text-left cursor-pointer rounded-[var(--radius)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] focus-visible:ring-offset-2"
      >
        <div className="relative aspect-[9/16] overflow-hidden rounded-[var(--radius)] border border-[var(--color-border)] bg-black transition-colors group-hover:border-[var(--color-text-muted)]">
          <video
            ref={videoRef}
            src={`${convertFileSrc(clip.clipPath)}#t=0.5`}
            preload="metadata"
            muted
            loop
            playsInline
            className={cn("h-full w-full", wide ? "object-contain" : "object-cover")}
          />
          {clip.durationSeconds > 0 && (
            <span className="absolute bottom-2 right-2 rounded-full bg-black/70 px-2 py-0.5 text-[11px] font-medium tabular-nums text-white">
              {duration(clip.durationSeconds)}
            </span>
          )}
        </div>
        <p className="mt-2.5 line-clamp-2 text-sm font-semibold text-[var(--color-text-primary)] leading-snug">
          {clip.title || clip.sessionTitle}
        </p>
        {shape && <p className="mt-0.5 text-xs text-[var(--color-text-muted)]">{shape}</p>}
      </button>
      <button
        type="button"
        onClick={onOpenSession}
        disabled={openingSession}
        aria-label={t("clipsPage.openSession", { id })}
        title={clip.sessionTitle}
        className="mt-1.5 flex w-full min-w-0 items-center gap-1.5 rounded-sm text-left text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] disabled:cursor-wait"
      >
        {openingSession ? (
          <Loader2 aria-hidden className="h-3 w-3 shrink-0 animate-spin" />
        ) : (
          <span className="shrink-0 font-mono text-[11px]">{id}</span>
        )}
        <span className="truncate">{clip.sessionTitle}</span>
      </button>
    </li>
  );
}

function EmptyState({ onAction }: { onAction: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="mx-auto mt-16 max-w-md text-center">
      <Film aria-hidden className="mx-auto h-10 w-10 text-[var(--color-text-muted)]" />
      <p className="mt-4 text-lg font-semibold text-[var(--color-text-primary)]">{t("clipsPage.empty.title")}</p>
      <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("clipsPage.empty.body")}</p>
      <Button onClick={onAction} className="mt-6 h-11 gap-2 px-5">
        {t("clipsPage.empty.cta")}
        <ArrowRight aria-hidden className="h-4 w-4" />
      </Button>
    </div>
  );
}
