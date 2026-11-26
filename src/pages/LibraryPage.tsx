import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Check, FolderOpen, Loader2, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { deleteSession, formatSessionId, listSessions, type SessionSummary } from "@/hooks/sessions";
import { useOpenSession } from "@/hooks/useOpenSession";
import { extractVideoId, getThumbnailUrl } from "@/utils/youtube";

/**
 * Projects (one highlight session each): one row per video, with plain progress ("2 of 5 clips
 * rendered") in place of the old Ready / Done labels, and a link to that
 * session's finished clips on the Clips page.
 */
export function LibraryPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<SessionSummary[] | null>(null);
  const [loading, setLoading] = useState(true);
  const { open, openingDir } = useOpenSession();

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setSessions(await listSessions());
    } catch (err) {
      console.error("Failed to list sessions", err);
      toast.error(t("library.loadFailed"));
      setSessions((prev) => prev ?? []);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    if (!iso || isNaN(d.getTime())) return "";
    return d.toLocaleString(i18n.language, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  };

  const remove = async (s: SessionSummary) => {
    try {
      await deleteSession(s.sessionDir);
      setSessions((prev) => prev?.filter((x) => x.sessionDir !== s.sessionDir) ?? null);
      toast.success(t("library.delete.done"));
    } catch (err) {
      console.error("Failed to delete session", err);
      toast.error(t("library.delete.failed"));
    }
  };

  return (
    <div className="mx-auto max-w-4xl py-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">{t("library.title")}</h1>
          <p className="mt-1 max-w-xl text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("library.subtitle")}</p>
        </div>
        <Button variant="outline" onClick={() => void refresh()} disabled={loading} className="h-10 gap-2">
          {loading ? <Loader2 aria-hidden className="h-4 w-4 animate-spin" /> : <RefreshCw aria-hidden className="h-4 w-4" />}
          {t("library.refresh")}
        </Button>
      </div>

      {sessions === null ? (
        <p className="mt-16 flex items-center justify-center gap-2 text-sm text-[var(--color-text-muted)]">
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          {t("library.loading")}
        </p>
      ) : sessions.length === 0 ? (
        <div className="mx-auto mt-16 max-w-md text-center">
          <FolderOpen aria-hidden className="mx-auto h-10 w-10 text-[var(--color-text-muted)]" />
          <p className="mt-4 text-lg font-semibold text-[var(--color-text-primary)]">{t("library.empty.title")}</p>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("library.empty.body")}</p>
          <Button onClick={() => navigate("/")} className="mt-6 h-11 gap-2 px-5">
            {t("library.empty.cta")}
            <ArrowRight aria-hidden className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <ul className="mt-6 divide-y divide-[var(--color-border)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)]">
          {sessions.map((s) => (
            <SessionRow
              key={s.sessionDir}
              session={s}
              date={formatDate(s.createdAt)}
              opening={openingDir === s.sessionDir}
              onOpen={() => void open(s.sessionDir)}
              onDelete={() => remove(s)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function SessionRow({
  session: s,
  date,
  opening,
  onOpen,
  onDelete,
}: {
  session: SessionSummary;
  date: string;
  opening: boolean;
  onOpen: () => void;
  onDelete: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const videoId = extractVideoId(s.url);
  const rendered = Math.min(s.renderedCount ?? 0, s.highlightCount || Infinity);
  const id = formatSessionId(s.id);

  return (
    <li className="flex items-center gap-2 bg-[var(--color-bg-primary)] pr-3 transition-colors hover:bg-[var(--color-bg-hover)]">
      <button
        type="button"
        onClick={onOpen}
        disabled={opening}
        className="flex min-w-0 flex-1 items-center gap-4 p-4 text-left cursor-pointer disabled:cursor-wait focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--color-border-focus)]"
      >
        <div className="relative aspect-video w-24 shrink-0 overflow-hidden sm:w-32 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-hover)]">
          {videoId && <img src={getThumbnailUrl(videoId, "mq")} alt="" loading="lazy" className="h-full w-full object-cover" />}
          {opening && (
            <span className="absolute inset-0 flex items-center justify-center bg-black/60">
              <Loader2 aria-hidden className="h-5 w-5 animate-spin text-white" />
            </span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="line-clamp-2 text-sm font-semibold text-[var(--color-text-primary)] leading-snug">{s.title}</p>
          <p className="mt-1 truncate text-xs text-[var(--color-text-muted)]">
            <span className="font-mono text-[11px]">{id}</span>
            {s.channel && <> · {s.channel}</>}
            {date && <> · {date}</>}
          </p>
          <p className="mt-2 flex items-center gap-1.5 text-xs">
            {rendered > 0 ? (
              <>
                <Check aria-hidden className="h-3.5 w-3.5 text-[var(--color-success)]" strokeWidth={3} />
                <span className="text-[var(--color-text-secondary)]">
                  {t("library.rendered", { done: rendered, total: s.highlightCount })}
                </span>
              </>
            ) : (
              <span className="text-[var(--color-text-muted)]">
                {t("library.highlights", { count: s.highlightCount })} · {t("library.notRendered")}
              </span>
            )}
          </p>
        </div>
      </button>

      {rendered > 0 && (
        <Link
          to={`/clips?session=${encodeURIComponent(s.id)}`}
          className="hidden shrink-0 items-center gap-1 rounded-full px-3 py-2 text-xs font-medium text-[var(--color-accent)] hover:bg-[var(--color-bg-card)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] sm:inline-flex"
        >
          {t("library.viewClips")}
          <ArrowRight aria-hidden className="h-3.5 w-3.5" />
        </Link>
      )}
      <DeleteButton rendered={rendered} onConfirm={onDelete} />
    </li>
  );
}

/** Deleting also removes finished videos, so it asks first and says how many. */
function DeleteButton({ rendered, onConfirm }: { rendered: number; onConfirm: () => Promise<void> }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const confirm = async () => {
    setBusy(true);
    await onConfirm();
    setBusy(false);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={(v) => !busy && setOpen(v)}>
      <PopoverTrigger
        aria-label={t("library.delete.label")}
        title={t("library.delete.label")}
        className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-bg-card)] hover:text-[var(--color-error)] data-[state=open]:text-[var(--color-error)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
      >
        <Trash2 aria-hidden className="h-4 w-4" />
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[min(300px,calc(100vw-2rem))]">
        <p className="text-sm font-semibold text-[var(--color-text-primary)]">{t("library.delete.title")}</p>
        <p className="mt-1.5 text-sm text-[var(--color-text-secondary)] leading-relaxed">
          {rendered > 0 ? t("library.delete.bodyClips", { count: rendered }) : t("library.delete.body")}
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={() => setOpen(false)} disabled={busy} className="h-9 px-3">
            {t("library.delete.cancel")}
          </Button>
          <Button variant="destructive" size="sm" onClick={() => void confirm()} disabled={busy} className="h-9 gap-1.5 px-3">
            {busy && <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />}
            {t("library.delete.confirm")}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
