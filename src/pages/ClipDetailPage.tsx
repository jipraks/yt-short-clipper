import { useEffect, useState, useCallback, useRef } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  Facebook,
  FolderOpen,
  Hash,
  Instagram,
  Loader2,
  Music2,
  RefreshCw,
  Sparkles,
  X,
  Youtube,
} from "lucide-react";
import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { toast } from "sonner";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { useConfigStore } from "@/stores/configStore";
import { inappSupported, useAccountStore } from "@/stores/accountStore";
import { aiBlocker, buildAIRequest } from "@/hooks/aiRuntime";
import { aiBlockerText } from "@/hooks/aiBlockerText";
import { replizListAccounts, replizUpload, type ReplizAccount } from "@/hooks/repliz";
import { formatSessionId } from "@/hooks/sessions";
import { useOpenSession } from "@/hooks/useOpenSession";
import { cn } from "@/lib/utils";
import replizMark from "@/assets/brands/repliz-mark.png";

const REPLIZ_SCHEDULE_URL = "https://repliz.com/user/schedule";

interface ScheduleOutcome {
  when: Date;
  accounts: ReplizAccount[];
  results: { account_id: string; success: boolean; message: string }[];
  /** Set when the upload itself failed, before any account was scheduled. */
  error?: string;
}

interface ClipDetailState {
  clipPath: string;
  title: string;
  hookText: string;
  description: string;
  startTime: string;
  endTime: string;
  sessionDir: string;
  highlightIndex: number;
  /** The source video's title, when the caller knows it (the Clips page does). */
  projectTitle?: string;
}

function platformIcon(type: string) {
  const cls = "h-4 w-4 shrink-0 text-[var(--color-text-secondary)]";
  switch (type) {
    case "youtube":
      return <Youtube aria-hidden className={cls} />;
    case "tiktok":
      return <Music2 aria-hidden className={cls} />;
    case "instagram":
      return <Instagram aria-hidden className={cls} />;
    case "facebook":
      return <Facebook aria-hidden className={cls} />;
    default:
      return <Hash aria-hidden className={cls} />;
  }
}

/** Tomorrow at 12:00 local time, in the shape a datetime-local input wants. */
function defaultScheduleValue(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(12, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function seconds(stamp: string): number {
  const [h = "0", m = "0", s = "0"] = stamp.split(",")[0].split(":");
  return Number(h) * 3600 + Number(m) * 60 + Number(s);
}

function clock(total: number): string {
  const s = Math.max(0, Math.round(total));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function ClipDetailPage() {
  const location = useLocation();
  const state = location.state as ClipDetailState | undefined;
  if (!state) return <Navigate to="/clips" replace />;
  return <ClipDetail state={state} />;
}

/**
 * One finished clip: watch it on the left, get it ready to post on the right
 * (title and description, then scheduling through Repliz). The only red button
 * is the one that posts.
 */
function ClipDetail({ state }: { state: ClipDetailState }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { config } = useConfigStore();
  const { activated, account, appInfo } = useAccountStore();
  const { open: openProject, openingDir } = useOpenSession();

  const [postTitle, setPostTitle] = useState(state.title || "");
  // The AI's write-up of the moment reads like a caption; the hook is a fallback.
  const [postDescription, setPostDescription] = useState(state.description || state.hookText || "");
  const [generating, setGenerating] = useState(false);

  const projectId = formatSessionId(state.sessionDir.split(/[\\/]/).filter(Boolean).pop() ?? "");
  const length = seconds(state.endTime) - seconds(state.startTime);

  const generate = async () => {
    const blocker = aiBlocker(config.ai, { activated, account, inappSupported: inappSupported(appInfo) });
    if (blocker) {
      toast.error(aiBlockerText(t, blocker));
      return;
    }
    setGenerating(true);
    try {
      const result = await invoke<{ title: string; description: string }>("generate_social_title", {
        title: state.title,
        hookText: state.hookText,
        description: state.description,
        ai: buildAIRequest(config.ai),
        // Lets the backend match the language this session was generated in.
        sessionDir: state.sessionDir,
      });
      if (result.title) setPostTitle(result.title);
      if (result.description) setPostDescription(result.description);
      toast.success(t("clipDetail.post.aiDone"));
    } catch (err) {
      toast.error(t("clipDetail.post.aiFailed", { reason: err instanceof Error ? err.message : String(err) }));
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl py-4">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="-ml-2 inline-flex min-h-10 items-center gap-1.5 rounded-full px-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
      >
        <ArrowLeft aria-hidden className="h-4 w-4" />
        {t("clipDetail.back")}
      </button>

      <div className="mt-6 grid gap-8 md:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        {/* The clip */}
        <div className="md:sticky md:top-4 md:self-start">
          <video
            src={convertFileSrc(state.clipPath)}
            controls
            playsInline
            className="mx-auto block aspect-[9/16] w-full max-w-[340px] rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-black object-contain"
          />
          <Button
            variant="ghost"
            onClick={() => invoke("open_path_in_explorer", { path: state.clipPath }).catch(console.error)}
            className="mt-2 h-10 w-full gap-2 text-[var(--color-text-secondary)]"
          >
            <FolderOpen aria-hidden className="h-4 w-4" />
            {t("clipDetail.openFolder")}
          </Button>
        </div>

        <div className="min-w-0">
          {/* Which clip, from where */}
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] leading-tight">{state.title}</h1>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">
            {length > 0 && <>{t("clipDetail.length", { length: clock(length) })} · </>}
            {t("clipDetail.range", { start: state.startTime, end: state.endTime })}
          </p>
          <button
            type="button"
            onClick={() => void openProject(state.sessionDir)}
            disabled={openingDir === state.sessionDir}
            aria-label={t("clipDetail.openProject", { id: projectId })}
            className="mt-2 inline-flex max-w-full items-center gap-1.5 rounded-sm text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] cursor-pointer disabled:cursor-wait focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            {openingDir === state.sessionDir && <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin" />}
            <span className="shrink-0">{t("clipDetail.fromProject", { id: projectId })}</span>
            {state.projectTitle && <span className="truncate text-[var(--color-text-muted)]">· {state.projectTitle}</span>}
            <ArrowRight aria-hidden className="h-3.5 w-3.5 shrink-0" />
          </button>

          {/* Title and description */}
          <section className="mt-8 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{t("clipDetail.post.title")}</h2>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("clipDetail.post.body")}</p>
              </div>
              <Button variant="outline" onClick={() => void generate()} disabled={generating} className="h-10 gap-2">
                {generating ? <Loader2 aria-hidden className="h-4 w-4 animate-spin" /> : <Sparkles aria-hidden className="h-4 w-4" />}
                {generating ? t("clipDetail.post.aiBusy") : t("clipDetail.post.ai")}
              </Button>
            </div>

            <CopyField
              id="post-title"
              label={t("clipDetail.post.fieldTitle")}
              value={postTitle}
              disabled={generating}
              onChange={setPostTitle}
              placeholder={t("clipDetail.post.titlePlaceholder")}
            />
            <CopyField
              id="post-description"
              label={t("clipDetail.post.fieldDescription")}
              value={postDescription}
              disabled={generating}
              onChange={setPostDescription}
              placeholder={t("clipDetail.post.descriptionPlaceholder")}
              multiline
            />
          </section>

          <ReplizSection clipPath={state.clipPath} title={postTitle} description={postDescription} />
        </div>
      </div>
    </div>
  );
}

/** A labelled text field with a copy button and a character count. */
function CopyField({
  id,
  label,
  value,
  onChange,
  placeholder,
  disabled,
  multiline,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  disabled?: boolean;
  multiline?: boolean;
}) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast.success(t("clipDetail.post.copied", { field: label }));
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("clipDetail.post.copyFailed"));
    }
  };

  return (
    <div className="mt-5">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <label htmlFor={id} className="text-xs font-medium text-[var(--color-text-muted)]">
          {label}
        </label>
        <div className="flex items-center gap-2">
          <span className="text-xs tabular-nums text-[var(--color-text-muted)]">
            {t("clipDetail.post.chars", { count: value.length })}
          </span>
          <button
            type="button"
            onClick={() => void copy()}
            disabled={!value}
            aria-label={t("clipDetail.post.copy", { field: label })}
            title={t("clipDetail.post.copy", { field: label })}
            className="inline-flex h-8 w-8 items-center justify-center rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            {copied ? <Check aria-hidden className="h-4 w-4 text-[var(--color-success)]" /> : <Copy aria-hidden className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {multiline ? (
        <textarea
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          rows={6}
          className="w-full resize-y rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] px-3 py-2.5 text-sm text-[var(--color-text-primary)] leading-relaxed placeholder:text-[var(--color-text-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] disabled:opacity-60"
        />
      ) : (
        <Input id={id} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} disabled={disabled} className="h-11" />
      )}
    </div>
  );
}

/** Scheduling through Repliz, or a short pitch with a way to connect it. */
function ReplizSection({ clipPath, title, description }: { clipPath: string; title: string; description: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { config } = useConfigStore();
  const configured = config.repliz.accessKey.trim() !== "" && config.repliz.secretKey.trim() !== "";

  const [accounts, setAccounts] = useState<ReplizAccount[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [scheduleAt, setScheduleAt] = useState(defaultScheduleValue());
  const [uploading, setUploading] = useState(false);
  const [outcome, setOutcome] = useState<ScheduleOutcome | null>(null);
  const loadedFor = useRef("");

  const load = useCallback(async () => {
    if (!configured) return;
    setLoading(true);
    setLoadError(null);
    try {
      setAccounts(await replizListAccounts(config.repliz.accessKey, config.repliz.secretKey));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [config.repliz.accessKey, config.repliz.secretKey, configured]);

  useEffect(() => {
    const key = `${config.repliz.accessKey}:${config.repliz.secretKey}`;
    if (!configured || loadedFor.current === key) return;
    loadedFor.current = key;
    void load();
  }, [configured, config.repliz.accessKey, config.repliz.secretKey, load]);

  const connected = accounts.filter((a) => a.is_connected);

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const upload = async () => {
    if (selected.size === 0) return toast.error(t("clipDetail.repliz.pickAccount"));
    if (!title.trim()) return toast.error(t("clipDetail.repliz.titleEmpty"));
    const when = new Date(scheduleAt);
    const now = new Date();
    if (isNaN(when.getTime()) || when <= now) return toast.error(t("clipDetail.repliz.past"));
    if (when.getTime() > now.getTime() + 7 * 24 * 60 * 60 * 1000) return toast.error(t("clipDetail.repliz.tooFar"));

    setUploading(true);
    setOutcome(null);
    const picked = accounts.filter((a) => selected.has(a.id));
    try {
      const result = await replizUpload({
        accessKey: config.repliz.accessKey,
        secretKey: config.repliz.secretKey,
        videoPath: clipPath,
        title: title.trim(),
        description: description.trim(),
        accountIds: [...selected],
        scheduleAt: when.toISOString(),
        onLog: (msg) => console.log("[repliz]", msg),
      });
      setOutcome({ when, accounts: picked, results: result.results });
    } catch (err) {
      setOutcome({ when, accounts: picked, results: [], error: err instanceof Error ? err.message : String(err) });
    } finally {
      setUploading(false);
    }
  };

  return (
    <section className="mt-6 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <img src={replizMark} alt="" aria-hidden className="mt-0.5 h-6 w-auto shrink-0" />
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{t("clipDetail.repliz.title")}</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              {configured ? t("clipDetail.repliz.body") : t("clipDetail.repliz.notConnected")}
            </p>
          </div>
        </div>
        {configured && (
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            aria-label={t("clipDetail.repliz.refresh")}
            title={t("clipDetail.repliz.refresh")}
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] cursor-pointer disabled:cursor-wait focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            <RefreshCw aria-hidden className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
        )}
      </div>

      {!configured ? (
        <Button variant="outline" onClick={() => navigate("/repliz")} className="mt-5 h-11 gap-2 px-5">
          {t("clipDetail.repliz.connect")}
          <ArrowRight aria-hidden className="h-4 w-4" />
        </Button>
      ) : loading && accounts.length === 0 ? (
        <p className="mt-5 flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          {t("clipDetail.repliz.loading")}
        </p>
      ) : loadError ? (
        <p className="mt-5 text-sm text-[var(--color-error)]">{t("clipDetail.repliz.loadFailed", { reason: loadError })}</p>
      ) : connected.length === 0 ? (
        <p className="mt-5 text-sm text-[var(--color-text-secondary)]">{t("clipDetail.repliz.noAccounts")}</p>
      ) : (
        <>
          <p id="repliz-accounts" className="mt-5 mb-2 text-xs font-medium text-[var(--color-text-muted)]">
            {t("clipDetail.repliz.accounts")}
          </p>
          <div role="group" aria-labelledby="repliz-accounts" className="grid gap-2 sm:grid-cols-2">
            {connected.map((acc) => {
              const on = selected.has(acc.id);
              return (
                <button
                  key={acc.id}
                  type="button"
                  role="checkbox"
                  aria-checked={on}
                  onClick={() => toggle(acc.id)}
                  className={cn(
                    "flex min-w-0 items-center gap-3 rounded-[var(--radius)] border px-3 py-2.5 text-left transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]",
                    on ? "border-[var(--color-accent)] bg-[var(--color-bg-hover)]" : "border-[var(--color-border)] hover:border-[var(--color-text-muted)]",
                  )}
                >
                  {platformIcon(acc.type)}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-[var(--color-text-primary)]">{acc.name}</span>
                    {acc.username && <span className="block truncate text-xs text-[var(--color-text-muted)]">@{acc.username}</span>}
                  </span>
                  <span
                    aria-hidden
                    className={cn(
                      "flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors",
                      on ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-[var(--color-bg-primary)]" : "border-[var(--color-border)]",
                    )}
                  >
                    {on && <Check className="h-3 w-3" strokeWidth={3} />}
                  </span>
                </button>
              );
            })}
          </div>

          <label htmlFor="repliz-when" className="mt-5 mb-2 block text-xs font-medium text-[var(--color-text-muted)]">
            {t("clipDetail.repliz.when")}
          </label>
          <Input
            id="repliz-when"
            type="datetime-local"
            value={scheduleAt}
            onChange={(e) => setScheduleAt(e.target.value)}
            className="h-11 w-full sm:w-auto [color-scheme:dark]"
          />
          <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">{t("clipDetail.repliz.whenHint")}</p>

          <Button
            onClick={() => void upload()}
            disabled={uploading || selected.size === 0}
            className="mt-6 h-12 w-full gap-2 text-base font-semibold"
          >
            {uploading && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
            {uploading
              ? t("clipDetail.repliz.submitting")
              : selected.size === 0
                ? t("clipDetail.repliz.submitNone")
                : t("clipDetail.repliz.submit", { count: selected.size })}
            {!uploading && selected.size > 0 && <ArrowRight aria-hidden className="h-4 w-4" />}
          </Button>
        </>
      )}

      {outcome && (
        <ScheduleResultDialog
          outcome={outcome}
          onClose={() => setOutcome(null)}
          onRetry={() => {
            setOutcome(null);
            void upload();
          }}
        />
      )}
    </section>
  );
}

/** Upload errors arrive with the sidecar's stderr attached; keep the first part. */
function shortReason(message: string): string {
  return message.split("\n\nstderr:")[0].replace(/^Sidecar error: /, "").trim();
}

/**
 * What happened after "Schedule": when it posts, and each account's result,
 * with a way into the Repliz schedule to see or change it.
 */
function ScheduleResultDialog({
  outcome,
  onClose,
  onRetry,
}: {
  outcome: ScheduleOutcome;
  onClose: () => void;
  onRetry: () => void;
}) {
  const { t, i18n } = useTranslation();
  const total = outcome.results.length;
  const ok = outcome.results.filter((r) => r.success).length;
  const kind = outcome.error ? "error" : ok === 0 ? "none" : ok === total ? "all" : "partial";

  const title =
    kind === "all"
      ? t("clipDetail.repliz.result.titleAll")
      : kind === "partial"
        ? t("clipDetail.repliz.result.titlePartial")
        : kind === "none"
          ? t("clipDetail.repliz.result.titleNone")
          : t("clipDetail.repliz.result.titleError");
  const body =
    kind === "all"
      ? t("clipDetail.repliz.result.bodyAll", { count: ok })
      : kind === "partial"
        ? t("clipDetail.repliz.result.bodyPartial", { ok, total })
        : kind === "none"
          ? t("clipDetail.repliz.result.bodyNone")
          : t("clipDetail.repliz.result.bodyError");

  const when = outcome.when.toLocaleString(i18n.language, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const openSchedule = () => {
    openUrl(REPLIZ_SCHEDULE_URL).catch((err) => console.error("Failed to open Repliz", err));
  };

  const badge = (good: boolean) => (
    <span
      className={cn(
        "flex h-7 w-7 items-center justify-center rounded-full text-[var(--color-bg-primary)]",
        good ? "bg-[var(--color-success)]" : "bg-[var(--color-error)]",
      )}
    >
      {good ? <Check aria-hidden className="h-4 w-4" strokeWidth={3} /> : <X aria-hidden className="h-4 w-4" strokeWidth={3} />}
    </span>
  );

  return (
    <Modal
      title={title}
      icon={kind === "all" ? badge(true) : kind === "partial" ? undefined : badge(false)}
      closeLabel={t("clipDetail.repliz.result.close")}
      onClose={onClose}
      className="max-w-lg"
    >
      {(close) => (
        <>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{body}</p>

          {kind !== "error" && (
            <div className="mt-5 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] px-4 py-3">
              <p className="text-xs font-medium text-[var(--color-text-muted)]">{t("clipDetail.repliz.result.when")}</p>
              <p className="mt-0.5 text-base font-semibold text-[var(--color-text-primary)]">{when}</p>
            </div>
          )}

          {kind === "error" ? (
            <p className="mt-4 max-h-32 overflow-y-auto whitespace-pre-line break-words text-sm text-[var(--color-error)]">
              {t("clipDetail.repliz.failed", { reason: shortReason(outcome.error ?? "") })}
            </p>
          ) : (
            <>
              <p className="mt-5 mb-2 text-xs font-medium text-[var(--color-text-muted)]">{t("clipDetail.repliz.result.accounts")}</p>
              <ul className="divide-y divide-[var(--color-border)] rounded-[var(--radius)] border border-[var(--color-border)]">
                {outcome.results.map((r) => {
                  const acc = outcome.accounts.find((a) => a.id === r.account_id);
                  return (
                    <li key={r.account_id} className="flex items-start gap-3 px-4 py-3">
                      <span className="mt-0.5">{platformIcon(acc?.type ?? "")}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-[var(--color-text-primary)]">
                          {acc?.name ?? r.account_id}
                        </span>
                        {acc?.username && (
                          <span className="block truncate text-xs text-[var(--color-text-muted)]">@{acc.username}</span>
                        )}
                        {!r.success && (
                          <span className="mt-1 block break-words text-xs text-[var(--color-error)]">
                            {t("clipDetail.repliz.result.failedItem", { reason: r.message })}
                          </span>
                        )}
                      </span>
                      {r.success && (
                        <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-[var(--color-success)]">
                          <Check aria-hidden className="h-3.5 w-3.5" strokeWidth={3} />
                          {t("clipDetail.repliz.result.scheduled")}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </>
          )}

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button variant="ghost" onClick={close} className="h-11 px-5">
              {t("clipDetail.repliz.result.close")}
            </Button>
            {ok > 0 ? (
              <Button onClick={openSchedule} className="h-11 gap-2 px-5">
                {t("clipDetail.repliz.result.openSchedule")}
                <ArrowRight aria-hidden className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={onRetry} className="h-11 px-5">
                {t("clipDetail.repliz.result.retry")}
              </Button>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
