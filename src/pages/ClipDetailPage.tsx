import { useEffect, useState, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Copy,
  Check,
  Loader2,
  Sparkles,
  FolderOpen,
  Upload,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Youtube,
  Music2,
  Instagram,
  Facebook,
  Hash,
} from "lucide-react";
import { invoke, convertFileSrc } from "@tauri-apps/api/core";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useConfigStore } from "@/stores/configStore";
import {
  replizListAccounts,
  replizUpload,
  type ReplizAccount,
} from "@/hooks/repliz";

interface ClipDetailState {
  clipPath: string;
  title: string;
  hookText: string;
  description: string;
  startTime: string;
  endTime: string;
  sessionDir: string;
  highlightIndex: number;
}

function platformIcon(type: string) {
  switch (type) {
    case "youtube":
      return <Youtube className="w-4 h-4 text-red-500" />;
    case "tiktok":
      return <Music2 className="w-4 h-4" />;
    case "instagram":
      return <Instagram className="w-4 h-4 text-pink-500" />;
    case "facebook":
      return <Facebook className="w-4 h-4 text-blue-500" />;
    case "threads":
      return <Hash className="w-4 h-4" />;
    default:
      return <Hash className="w-4 h-4 text-[var(--color-text-muted)]" />;
  }
}

// Default schedule: tomorrow at 12:00 local time, formatted for datetime-local input
function defaultScheduleValue(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(12, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function ClipDetailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { config } = useConfigStore();
  const state = location.state as ClipDetailState | undefined;

  const [postTitle, setPostTitle] = useState("");
  const [postDescription, setPostDescription] = useState("");
  const [generating, setGenerating] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Repliz state
  const [accounts, setAccounts] = useState<ReplizAccount[]>([]);
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());
  const [loadingAccounts, setLoadingAccounts] = useState(false);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [scheduleAt, setScheduleAt] = useState(defaultScheduleValue());
  const [uploading, setUploading] = useState(false);
  const [uploadResults, setUploadResults] = useState<
    { account_id: string; success: boolean; message: string }[] | null
  >(null);

  useEffect(() => {
    if (!state) navigate("/library");
  }, [state, navigate]);

  useEffect(() => {
    if (state) {
      setPostTitle(state.title || "");
      setPostDescription(state.hookText || "");
    }
  }, [state]);

  const replizConfigured =
    config.repliz.accessKey.trim() !== "" && config.repliz.secretKey.trim() !== "";

  const loadAccounts = useCallback(async () => {
    if (!replizConfigured) return;
    setLoadingAccounts(true);
    setAccountsError(null);
    try {
      const result = await replizListAccounts(
        config.repliz.accessKey,
        config.repliz.secretKey
      );
      setAccounts(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setAccountsError(msg);
    } finally {
      setLoadingAccounts(false);
    }
  }, [config.repliz, replizConfigured]);

  useEffect(() => {
    loadAccounts();
  }, [loadAccounts]);

  if (!state) return null;

  const videoSrc = convertFileSrc(state.clipPath);

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      // silent
    }
  };

  const generateTitles = async () => {
    const tg = config.ai;
    if (!tg.apiKey || !tg.model) {
      toast.error("AI provider not configured. Go to AI Models settings.");
      return;
    }

    setGenerating(true);
    try {
      const result = await invoke<{ title: string; description: string }>("generate_social_title", {
        title: state.title,
        hookText: state.hookText,
        description: state.description,
        apiKey: tg.apiKey,
        baseUrl: tg.baseUrl,
        model: tg.model,
        // Lets the backend match the language this session was generated in.
        sessionDir: state.sessionDir,
      });
      if (result.title) setPostTitle(result.title);
      if (result.description) setPostDescription(result.description);
      toast.success("Title & description generated");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Generation failed: ${msg}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleOpenFolder = () => {
    invoke("open_path_in_explorer", { path: state.clipPath }).catch(console.error);
  };

  const toggleAccount = (id: string) => {
    setSelectedAccounts((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleUpload = async () => {
    if (selectedAccounts.size === 0) {
      toast.error("Select at least one account");
      return;
    }
    if (!postTitle.trim()) {
      toast.error("Title cannot be empty");
      return;
    }

    // Validate schedule: must be future, within 7 days
    const scheduleDate = new Date(scheduleAt);
    const now = new Date();
    if (isNaN(scheduleDate.getTime()) || scheduleDate <= now) {
      toast.error("Schedule time must be in the future");
      return;
    }
    const maxDate = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    if (scheduleDate > maxDate) {
      toast.error("Schedule time cannot be more than 7 days ahead");
      return;
    }

    setUploading(true);
    setUploadResults(null);
    try {
      const result = await replizUpload({
        accessKey: config.repliz.accessKey,
        secretKey: config.repliz.secretKey,
        videoPath: state.clipPath,
        title: postTitle.trim(),
        description: postDescription.trim(),
        accountIds: [...selectedAccounts],
        scheduleAt: scheduleDate.toISOString(),
        onLog: (msg) => console.log("[repliz]", msg),
      });
      setUploadResults(result.results);
      const okCount = result.results.filter((r) => r.success).length;
      if (okCount === result.results.length) {
        toast.success(`Scheduled to ${okCount} account(s)`);
      } else {
        toast.warning(`Scheduled to ${okCount}/${result.results.length} account(s)`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Upload failed: ${msg}`);
    } finally {
      setUploading(false);
    }
  };

  const connectedAccounts = accounts.filter((a) => a.is_connected);

  return (
    <div className="space-y-5 max-w-3xl">
      <Button
        variant="ghost"
        onClick={() => navigate(-1)}
        className="gap-2 text-[var(--color-text-secondary)]"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </Button>

      <div>
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">{state.title}</h2>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          {state.startTime} → {state.endTime}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Left: Video player */}
        <div className="space-y-3">
          <Card className="p-0 overflow-hidden bg-black">
            <video
              src={videoSrc}
              controls
              className="w-full"
              style={{ aspectRatio: "9/16", maxWidth: "300px", margin: "0 auto", display: "block" }}
            />
          </Card>
          <Button variant="outline" size="sm" onClick={handleOpenFolder} className="gap-2 w-full">
            <FolderOpen className="w-4 h-4" />
            Open in Explorer
          </Button>
        </div>

        {/* Right: Post details */}
        <div className="space-y-4">
          {/* Title & Description editor */}
          <Card className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase">
                Post Details
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={generateTitles}
                disabled={generating}
                className="gap-2"
              >
                {generating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                {generating ? "Generating..." : "Generate with AI"}
              </Button>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs text-[var(--color-text-muted)]">Title</label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(postTitle, "title")}
                  className="h-5 px-1.5 text-xs"
                >
                  {copiedField === "title" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                </Button>
              </div>
              <Input value={postTitle} onChange={(e) => setPostTitle(e.target.value)} placeholder="Post title" />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs text-[var(--color-text-muted)]">Description</label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(postDescription, "desc")}
                  className="h-5 px-1.5 text-xs"
                >
                  {copiedField === "desc" ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                </Button>
              </div>
              <textarea
                value={postDescription}
                onChange={(e) => setPostDescription(e.target.value)}
                placeholder="Post description with hashtags"
                rows={4}
                className="w-full rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] resize-none"
              />
            </div>
          </Card>
        </div>
      </div>

      {/* Repliz Upload */}
      <Card className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-[var(--color-accent)]" />
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">
              Upload via Repliz
            </span>
          </div>
          {replizConfigured && (
            <Button
              variant="ghost"
              size="sm"
              onClick={loadAccounts}
              disabled={loadingAccounts}
              className="h-7 gap-1.5 text-xs"
            >
              {loadingAccounts ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              Refresh
            </Button>
          )}
        </div>

        {!replizConfigured ? (
          <div className="text-sm text-[var(--color-text-muted)] py-4 text-center">
            Repliz is not configured.{" "}
            <button
              onClick={() => navigate("/settings/repliz")}
              className="text-[var(--color-accent)] underline"
            >
              Set up Repliz
            </button>{" "}
            to upload clips directly.
          </div>
        ) : loadingAccounts ? (
          <div className="flex items-center justify-center py-6 text-[var(--color-text-muted)]">
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Loading accounts...
          </div>
        ) : accountsError ? (
          <div className="text-sm text-[var(--color-error)] py-4 text-center">
            Failed to load accounts: {accountsError}
          </div>
        ) : connectedAccounts.length === 0 ? (
          <div className="text-sm text-[var(--color-text-muted)] py-4 text-center">
            No connected accounts. Connect your social media accounts in the Repliz dashboard first.
          </div>
        ) : (
          <>
            {/* Account selection */}
            <div className="space-y-2">
              <label className="text-xs text-[var(--color-text-muted)] uppercase">Select Platforms</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {connectedAccounts.map((acc) => {
                  const selected = selectedAccounts.has(acc.id);
                  return (
                    <button
                      key={acc.id}
                      onClick={() => toggleAccount(acc.id)}
                      className={`flex items-center gap-2 p-2.5 rounded-[var(--radius-sm)] border text-left transition-all ${
                        selected
                          ? "border-[var(--color-accent)] bg-[var(--color-accent)]/5"
                          : "border-[var(--color-border)] hover:border-[var(--color-border-focus)]"
                      }`}
                    >
                      {selected ? (
                        <CheckCircle2 className="w-4 h-4 text-[var(--color-accent)] shrink-0" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-[var(--color-border)] shrink-0" />
                      )}
                      {platformIcon(acc.type)}
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                          {acc.name}
                        </p>
                        {acc.username && (
                          <p className="text-xs text-[var(--color-text-muted)] truncate">
                            @{acc.username}
                          </p>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Schedule */}
            <div className="space-y-2">
              <label className="text-xs text-[var(--color-text-muted)] uppercase">
                Schedule (max 7 days ahead)
              </label>
              <Input
                type="datetime-local"
                value={scheduleAt}
                onChange={(e) => setScheduleAt(e.target.value)}
                className="w-full"
              />
            </div>

            {/* Upload results */}
            {uploadResults && (
              <div className="space-y-1.5">
                {uploadResults.map((r) => {
                  const acc = accounts.find((a) => a.id === r.account_id);
                  return (
                    <div key={r.account_id} className="flex items-center gap-2 text-sm">
                      {r.success ? (
                        <CheckCircle2 className="w-4 h-4 text-[var(--color-success)] shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-[var(--color-error)] shrink-0" />
                      )}
                      <span className="text-[var(--color-text-secondary)]">
                        {acc?.name ?? r.account_id}: {r.message}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Upload button */}
            <Button
              onClick={handleUpload}
              disabled={uploading || selectedAccounts.size === 0}
              className="w-full h-11 gap-2"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading & scheduling...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload to {selectedAccounts.size} platform{selectedAccounts.size === 1 ? "" : "s"}
                </>
              )}
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
