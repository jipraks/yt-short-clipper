import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Clipboard, Play, CirclePlay, Cookie, CheckCircle2, Loader2, ExternalLink, Captions, CaptionsOff, Wand2, ChevronDown } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { CookiesDialog } from "@/components/CookiesDialog";
import { extractVideoId, getThumbnailUrl } from "@/utils/youtube";
import { useProcessingStore } from "@/stores/processingStore";
import { useCookiesStore } from "@/stores/cookiesStore";
import { useConfigStore } from "@/stores/configStore";
import {
  getAvailableSubtitles,
  normalizeSubtitleOptions,
  type SubtitleOption,
} from "@/hooks/subtitles";
import {
  AUTO_LANGUAGE,
  OUTPUT_LANGUAGES,
  languageNameForCode,
} from "@/config/languages";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

type SubtitleState = "idle" | "loading" | "loaded" | "empty" | "error";

/** Character budget for the optional AI direction, mirrored in the backend. */
const DIRECTION_MAX = 1000;

const DIRECTION_PLACEHOLDER =
  'e.g. Clip 1 from 21:30 to 22:25. Take every mention of "investment". Skip the intro and the sponsor read.';

/** Tap-to-insert starters showing the kinds of steer the prompt understands. */
const DIRECTION_EXAMPLES: { label: string; text: string }[] = [
  {
    label: "Cut from a specific time",
    text: "Only use the part between 5:10 and 12:00.",
  },
  {
    label: "Every time a topic comes up",
    text: "Take every moment where they talk about pricing.",
  },
  {
    label: "One moment first, then the rest",
    text: "There is a punchline during the roasting bit — clip that first, then fill the rest with the funniest moments.",
  },
  {
    label: "Things to stay away from",
    text: "Skip the intro and any sponsor read, and avoid heavy or sad topics.",
  },
];

export function CreatePage() {
  const navigate = useNavigate();
  const { start } = useProcessingStore();
  const { cookiesValid, checkCookies } = useCookiesStore();
  const { config, loaded: configLoaded, load: loadConfig } = useConfigStore();

  const [url, setUrl] = useState("");
  const [clipCount, setClipCount] = useState(5);
  const [subtitleLang, setSubtitleLang] = useState("");
  const [showCookiesDialog, setShowCookiesDialog] = useState(false);
  const [outputLanguage, setOutputLanguage] = useState(AUTO_LANGUAGE);
  const [userDirection, setUserDirection] = useState("");
  const [directionOpen, setDirectionOpen] = useState(false);
  const [showExamples, setShowExamples] = useState(false);

  const [subtitleState, setSubtitleState] = useState<SubtitleState>("idle");
  const [subtitleOptions, setSubtitleOptions] = useState<SubtitleOption[]>([]);
  const [subtitleError, setSubtitleError] = useState("");
  const [captionOrigCode, setCaptionOrigCode] = useState<string | null>(null);
  const fetchSeq = useRef(0);

  useEffect(() => {
    checkCookies();
    loadConfig();
  }, [checkCookies, loadConfig]);

  const videoId = extractVideoId(url);
  const thumbnailUrl = videoId ? getThumbnailUrl(videoId, "hq") : null;

  // Fetch subtitles whenever a valid video URL + valid cookies are present
  useEffect(() => {
    if (!videoId || !cookiesValid) {
      setSubtitleState("idle");
      setSubtitleOptions([]);
      setSubtitleLang("");
      setCaptionOrigCode(null);
      return;
    }

    const seq = ++fetchSeq.current;
    setSubtitleState("loading");
    setSubtitleOptions([]);
    setSubtitleLang("");
    setSubtitleError("");
    setCaptionOrigCode(null);

    getAvailableSubtitles(url)
      .then((result) => {
        if (seq !== fetchSeq.current) return; // stale response, ignore

        if (result.error) {
          setSubtitleState("error");
          setSubtitleError(result.error);
          return;
        }

        const options = normalizeSubtitleOptions(result);
        if (options.length === 0) {
          setSubtitleState("empty");
          return;
        }

        // Build unique key per option (code + type)
        setSubtitleOptions(options);
        setCaptionOrigCode(result.captionOrigCode ?? null);

        // Prefer the original-language track (genuine ASR, best transcript and
        // the source of word-level caption timing); fall back to id, then first.
        const preferred =
          (result.captionOrigCode
            ? options.find((o) => o.code === result.captionOrigCode)
            : undefined) ??
          options.find((o) => o.code === "id") ??
          options[0];
        setSubtitleLang(`${preferred.code}:${preferred.type}`);
        setSubtitleState("loaded");
      })
      .catch((err) => {
        if (seq !== fetchSeq.current) return;
        console.error("Failed to fetch subtitles", err);
        const detail =
          err instanceof Error
            ? err.message
            : typeof err === "string"
              ? err
              : JSON.stringify(err, null, 2);
        setSubtitleState("error");
        setSubtitleError(detail || "Failed to fetch subtitles");
      });
  }, [videoId, cookiesValid, url]);

  const subtitlesReady = subtitleState === "loaded" && subtitleLang !== "";
  const isValid = !!videoId && cookiesValid && subtitlesReady;

  const trimmedDirection = userDirection.trim();

  // What "Auto" resolves to, so the choice is visible before running.
  const autoLanguageName = languageNameForCode(subtitleLang.split(":")[0]);

  const addExample = useCallback((text: string) => {
    setUserDirection((current) => {
      const base = current.trim();
      return (base ? `${base} ${text}` : text).slice(0, DIRECTION_MAX);
    });
  }, []);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text.trim());
    } catch {
      // Clipboard API not available or denied
    }
  }, []);

  const handleStart = () => {
    if (!cookiesValid) {
      setShowCookiesDialog(true);
      return;
    }
    if (!isValid) return;

    const hf = config.ai;
    if (!configLoaded || !hf.apiKey.trim() || !hf.model.trim()) {
      toast.error("Configure the AI provider first");
      navigate("/ai-models");
      return;
    }

    // subtitleLang is stored as "code:type" — the backend only needs the code
    const subtitleCode = subtitleLang.split(":")[0];

    start({
      url,
      numClips: clipCount,
      subtitleLanguage: subtitleCode,
      userDirection: trimmedDirection || undefined,
      outputLanguage,
      ai: {
        api_key: hf.apiKey,
        base_url: hf.baseUrl,
        model: hf.model,
        system_message: hf.systemMessage,
      },
    });
    navigate("/processing");
  };

  const handleClipCountInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    if (!isNaN(val) && val >= 1 && val <= 10) {
      setClipCount(val);
    }
  };

  if (showCookiesDialog) {
    return (
      <CookiesDialog
        onDone={(valid) => {
          setShowCookiesDialog(false);
          if (valid) {
            checkCookies();
            toast.success("Cookies ready, fetching subtitles...");
          }
        }}
      />
    );
  }

  return (
    <div className="space-y-5">
      {/* URL Input */}
      <div className="flex gap-2">
        <Input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="YouTube URL"
          className="flex-1 h-12 text-base rounded-[var(--radius)] border-[var(--color-border)] bg-[var(--color-bg-primary)] shadow-[var(--shadow-sm)]"
        />
        <Button
          variant="outline"
          onClick={handlePaste}
          className="h-12 px-4 gap-2 rounded-[var(--radius)] shadow-[var(--shadow-sm)]"
        >
          <Clipboard className="w-4 h-4" />
          Paste
        </Button>
      </div>

      {/* Main content: Clip Parameters + Thumbnail */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Left: Clip Parameters */}
        <Card>
          <CardHeader>
            <CardTitle>Clip Parameters</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Subtitle Language */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm font-medium text-[var(--color-text-secondary)]">
                Subtitle Language:
                {subtitleState === "loading" && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--color-accent)]" />
                )}
              </label>
              <select
                value={subtitleLang}
                onChange={(e) => setSubtitleLang(e.target.value)}
                disabled={subtitleState !== "loaded"}
                className="w-full h-10 px-3 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {subtitleState === "loaded" ? (
                  subtitleOptions.map((opt) => (
                    <option key={`${opt.code}:${opt.type}`} value={`${opt.code}:${opt.type}`}>
                      {opt.code} - {opt.name}
                      {opt.type === "auto" ? " (auto)" : ""}
                    </option>
                  ))
                ) : (
                  <option value="">
                    {subtitleState === "idle" && "Paste a YouTube URL first"}
                    {subtitleState === "loading" && "Loading subtitles..."}
                    {subtitleState === "empty" && "No subtitles available"}
                    {subtitleState === "error" && "Failed to load subtitles"}
                  </option>
                )}
              </select>
              {subtitleState === "loaded" && (
                captionOrigCode ? (
                  <p className="flex items-center gap-1.5 text-xs text-[var(--color-success)]">
                    <Captions className="w-3.5 h-3.5 shrink-0" />
                    Original subtitle available ({captionOrigCode}) — clips will get word-by-word captions
                  </p>
                ) : (
                  <p className="flex items-center gap-1.5 text-xs text-[var(--color-warning)]">
                    <CaptionsOff className="w-3.5 h-3.5 shrink-0" />
                    No original subtitle — clips will be created without captions
                  </p>
                )
              )}
              {subtitleState === "empty" && (
                <p className="text-xs text-[var(--color-warning)]">
                  This video has no subtitles. Try another video.
                </p>
              )}
              {subtitleState === "error" && (
                <p className="text-xs text-[var(--color-error)] whitespace-pre-line max-h-32 overflow-y-auto font-mono bg-[var(--color-error-bg)] rounded-[var(--radius-sm)] p-2">
                  {subtitleError}
                </p>
              )}
            </div>

            {/* Output Language */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                Output Language:
              </label>
              <select
                value={outputLanguage}
                onChange={(e) => setOutputLanguage(e.target.value)}
                className="w-full h-10 px-3 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] transition-all cursor-pointer"
              >
                <option value={AUTO_LANGUAGE}>
                  Auto{autoLanguageName ? ` \u2014 ${autoLanguageName}` : " \u2014 match the video"}
                </option>
                {OUTPUT_LANGUAGES.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-[var(--color-text-muted)]">
                Language for clip titles and on-screen hook text. Auto follows the video, which
                keeps the hook in the same language as the burned-in captions.
              </p>
            </div>

            {/* Clip Count */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Clip Count:
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={clipCount}
                  onChange={handleClipCountInput}
                  className="w-14 h-8 text-center text-sm font-semibold rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)]"
                />
              </div>
              <Slider
                value={[clipCount]}
                onValueChange={(val) => setClipCount(val[0])}
                min={1}
                max={10}
                step={1}
              />
              <div className="flex justify-between text-xs text-[var(--color-text-muted)]">
                <span>1</span>
                <span>10</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Right: Thumbnail Preview */}
        <Card className="flex items-center justify-center min-h-[220px]">
          {thumbnailUrl ? (
            <img
              src={thumbnailUrl}
              alt="Video thumbnail"
              className="w-full h-full object-cover rounded-[var(--radius-sm)]"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          ) : (
            <div className="flex flex-col items-center gap-3 text-[var(--color-text-muted)]">
              <CirclePlay className="w-12 h-12 opacity-40" />
              <span className="text-sm">Video thumbnail will appear here</span>
            </div>
          )}
        </Card>
      </div>

      {/* AI Direction (optional) */}
      <Card className="p-0 overflow-hidden">
        <button
          type="button"
          onClick={() => setDirectionOpen((open) => !open)}
          className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left cursor-pointer hover:bg-[var(--color-bg-hover)] transition-colors"
        >
          <span className="flex items-center gap-2.5 min-w-0">
            <Wand2 className="w-4 h-4 shrink-0 text-[var(--color-accent)]" />
            <span className="text-base font-semibold text-[var(--color-text-primary)] shrink-0">
              Direct the AI
            </span>
            <span className="text-xs text-[var(--color-text-muted)] shrink-0">(optional)</span>
            {!directionOpen && trimmedDirection !== "" && (
              <span className="truncate text-xs text-[var(--color-accent)]">
                {trimmedDirection}
              </span>
            )}
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 shrink-0 text-[var(--color-text-muted)] transition-transform duration-200",
              directionOpen && "rotate-180"
            )}
          />
        </button>

        {directionOpen && (
          <div className="px-5 pb-5 pt-4 space-y-3 border-t border-[var(--color-border-light)]">
            <p className="text-xs text-[var(--color-text-secondary)]">
              Leave it empty and the AI picks on its own. Or tell it what to go after — a
              time range, a recurring topic, or what to stay away from.
            </p>

            <textarea
              value={userDirection}
              onChange={(e) => setUserDirection(e.target.value.slice(0, DIRECTION_MAX))}
              maxLength={DIRECTION_MAX}
              placeholder={DIRECTION_PLACEHOLDER}
              className="w-full min-h-[110px] px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)] resize-y"
            />

            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setUserDirection("")}
                disabled={userDirection === ""}
                className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                Clear
              </button>
              <span className="text-xs text-[var(--color-text-muted)] tabular-nums">
                {userDirection.length}/{DIRECTION_MAX}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setShowExamples((show) => !show)}
              className="flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline cursor-pointer"
            >
              {showExamples ? "Hide examples" : "Show examples"}
              <ChevronDown
                className={cn(
                  "w-3 h-3 transition-transform duration-200",
                  showExamples && "rotate-180"
                )}
              />
            </button>

            {showExamples && (
              <div className="space-y-2 rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-secondary)] p-3">
                <p className="text-xs text-[var(--color-text-muted)]">
                  Tap one to add it to the box above.
                </p>
                {DIRECTION_EXAMPLES.map((example) => (
                  <button
                    key={example.label}
                    type="button"
                    onClick={() => addExample(example.text)}
                    className="w-full text-left px-3 py-2 rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-primary)] hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-light)] transition-colors cursor-pointer"
                  >
                    <span className="block text-[11px] text-[var(--color-text-muted)]">
                      {example.label}
                    </span>
                    <span className="block mt-0.5 text-xs text-[var(--color-text-primary)]">
                      “{example.text}”
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Cookies Status */}
      <div
        className={`flex items-center justify-between p-3 rounded-[var(--radius-sm)] border cursor-pointer transition-all duration-200 ${
          cookiesValid
            ? "bg-[var(--color-success-bg)] border-[var(--color-success)]/30 text-[var(--color-success)]"
            : "bg-[var(--color-warning-bg)] border-[var(--color-warning)]/30 text-[var(--color-warning)]"
        }`}
        onClick={() => setShowCookiesDialog(true)}
      >
        <div className="flex items-center gap-2 text-sm font-medium">
          {cookiesValid ? (
            <>
              <CheckCircle2 className="w-4 h-4" />
              <span>YouTube cookies loaded</span>
            </>
          ) : (
            <>
              <Cookie className="w-4 h-4" />
              <span>Upload YouTube cookies to continue</span>
            </>
          )}
        </div>
        <span className="text-xs underline">
          {cookiesValid ? "Change" : "Upload"}
        </span>
      </div>

      {/* Help link */}
      {!cookiesValid && (
        <button
          onClick={() => openUrl("https://github.com/jipraks/yt-short-clipper#youtube-cookies")}
          className="flex items-center gap-1 text-xs text-[var(--color-accent)] hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          Need help? View cookies setup guide
        </button>
      )}

      {/* CTA Button */}
      <Button
        size="lg"
        disabled={!isValid}
        onClick={handleStart}
        className="w-full h-14 text-base font-semibold rounded-[var(--radius)] shadow-[var(--shadow)] gap-2"
      >
        <Play className="w-5 h-5" />
        Find Highlights →
      </Button>
    </div>
  );
}
