import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  FolderOpen,
  Loader2,
  RefreshCw,
  Trash2,
  Clock,
  Film,
  CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  listSessions,
  loadSession,
  deleteSession,
  type SessionSummary,
} from "@/hooks/sessions";
import { useSessionStore } from "@/stores/sessionStore";

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function LibraryPage() {
  const navigate = useNavigate();
  const { setSession } = useSessionStore();
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [openingDir, setOpeningDir] = useState<string | null>(null);
  const [deletingDir, setDeletingDir] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listSessions();
      setSessions(result);
    } catch (err) {
      console.error("Failed to list sessions", err);
      toast.error("Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleOpen = async (summary: SessionSummary) => {
    setOpeningDir(summary.sessionDir);
    try {
      const session = await loadSession(summary.sessionDir);
      setSession(session, "library");

      if (summary.status === "completed") {
        // Already processed — go straight to highlights with a note
        toast.info("This session has already been processed");
      }

      navigate("/highlights");
    } catch (err) {
      console.error("Failed to open session", err);
      toast.error("Failed to open session");
    } finally {
      setOpeningDir(null);
    }
  };

  const handleDelete = async (summary: SessionSummary, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeletingDir(summary.sessionDir);
    try {
      await deleteSession(summary.sessionDir);
      setSessions((prev) => prev.filter((s) => s.sessionDir !== summary.sessionDir));
      toast.success("Session deleted");
    } catch (err) {
      console.error("Failed to delete session", err);
      toast.error("Failed to delete session");
    } finally {
      setDeletingDir(null);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Library</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Your previous highlight sessions.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={loading} className="gap-2">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-[var(--color-text-muted)]">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading sessions...
        </div>
      ) : sessions.length === 0 ? (
        <Card className="flex flex-col items-center justify-center py-16 gap-4">
          <FolderOpen className="w-16 h-16 text-[var(--color-text-muted)] opacity-40" />
          <div className="text-center space-y-1">
            <p className="text-base font-medium text-[var(--color-text-secondary)]">
              No sessions yet
            </p>
            <p className="text-sm text-[var(--color-text-muted)]">
              Your clipping sessions will appear here after finding highlights.
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {sessions.map((s) => (
            <Card
              key={s.sessionDir}
              className="p-4 cursor-pointer transition-all duration-200 hover:border-[var(--color-accent)]/40 hover:shadow-[var(--shadow)]"
              onClick={() => handleOpen(s)}
            >
              <div className="flex items-center gap-4">
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
                    {s.title}
                  </p>
                  {s.channel && (
                    <p className="text-xs text-[var(--color-text-muted)] truncate">{s.channel}</p>
                  )}
                  <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)] pt-1">
                    <span className="flex items-center gap-1">
                      <Film className="w-3.5 h-3.5" />
                      {s.highlightCount} highlights
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatDate(s.createdAt)}
                    </span>
                    {s.status === "highlights_found" ? (
                      <span className="flex items-center gap-1 text-[var(--color-success)]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Ready
                      </span>
                    ) : s.status === "completed" ? (
                      <span className="flex items-center gap-1 text-[var(--color-accent)]">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Done
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {openingDir === s.sessionDir ? (
                    <Loader2 className="w-4 h-4 animate-spin text-[var(--color-text-muted)]" />
                  ) : (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleDelete(s, e)}
                      disabled={deletingDir === s.sessionDir}
                      className="h-8 w-8 text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
                    >
                      {deletingDir === s.sessionDir ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
