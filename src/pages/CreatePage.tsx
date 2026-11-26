import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, ChevronDown, Info, Link2, Minus, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Combobox, type ComboboxGroup } from "@/components/ui/combobox";
import { Wordmark } from "@/components/brand/Wordmark";
import { CookiesDialog } from "@/components/CookiesDialog";
import { BlockingProgress } from "@/components/BlockingProgress";
import { extractVideoId, fetchVideoInfo, getThumbnailUrl, type VideoInfo } from "@/utils/youtube";
import { useProcessingStore } from "@/stores/processingStore";
import { useCookiesStore } from "@/stores/cookiesStore";
import { useConfigStore } from "@/stores/configStore";
import { inappSupported, useAccountStore } from "@/stores/accountStore";
import { aiBlocker, buildAIRequest } from "@/hooks/aiRuntime";
import { aiBlockerText } from "@/hooks/aiBlockerText";
import { getAvailableSubtitles, normalizeSubtitleOptions, type SubtitleOption } from "@/hooks/subtitles";
import { AUTO_LANGUAGE, OUTPUT_LANGUAGES, languageNameForCode } from "@/config/languages";
import { cn } from "@/lib/utils";

type SubtitleState = "idle" | "loading" | "loaded" | "empty" | "error";

/** Character budget for the optional AI direction, mirrored in the backend. */
const DIRECTION_MAX = 1000;
const EXAMPLE_KEYS = ["range", "topic", "first", "avoid"] as const;
const MIN_CLIPS = 1;
const MAX_CLIPS = 10;

const chip =
  "inline-flex h-11 items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-primary)] px-4 text-sm text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-bg-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

/** A language name in the UI's language ("Japanese" reads "Jepang" in Indonesian). */
function useLanguageName() {
  const { i18n } = useTranslation();
  return useCallback(
    (code: string, fallback?: string) => {
      try {
        const name = new Intl.DisplayNames([i18n.language], { type: "language" }).of(code);
        if (name && name.toLowerCase() !== code.toLowerCase()) return name.charAt(0).toUpperCase() + name.slice(1);
      } catch {
        // Fall back to the names below.
      }
      return languageNameForCode(code) ?? fallback ?? code;
    },
    [i18n.language],
  );
}

export function CreatePage() {
  const { t } = useTranslation();
  const languageName = useLanguageName();
  const navigate = useNavigate();
  const { start } = useProcessingStore();
  const { cookiesValid, checkCookies } = useCookiesStore();
  const { config, loaded: configLoaded, load: loadConfig } = useConfigStore();
  const { activated, account, appInfo } = useAccountStore();

  const [url, setUrl] = useState("");
  const [clipCount, setClipCount] = useState(5);
  const [subtitleLang, setSubtitleLang] = useState("");
  const [showCookiesDialog, setShowCookiesDialog] = useState(false);
  const [outputLanguage, setOutputLanguage] = useState(AUTO_LANGUAGE);
  const [userDirection, setUserDirection] = useState("");

  const [subtitleState, setSubtitleState] = useState<SubtitleState>("idle");
  const [subtitleOptions, setSubtitleOptions] = useState<SubtitleOption[]>([]);
  const [subtitleError, setSubtitleError] = useState("");
  const [captionOrigCode, setCaptionOrigCode] = useState<string | null>(null);
  const fetchSeq = useRef(0);
  // After subtitles load, point at the language to check and the button next.
  const [guide, setGuide] = useState(false);

  useEffect(() => {
    checkCookies();
    loadConfig();
  }, [checkCookies, loadConfig]);

  const videoId = extractVideoId(url);
  const thumbnailUrl = videoId ? getThumbnailUrl(videoId, "hq") : null;

  // Title and channel for the video card; the card still shows without them.
  const [videoInfo, setVideoInfo] = useState<VideoInfo | "loading" | null>(null);
  useEffect(() => {
    if (!videoId) {
      setVideoInfo(null);
      return;
    }
    const controller = new AbortController();
    setVideoInfo("loading");
    fetchVideoInfo(videoId, controller.signal).then((info) => {
      if (!controller.signal.aborted) setVideoInfo(info);
    });
    return () => controller.abort();
  }, [videoId]);

  // Fetch subtitles whenever a valid video URL + valid cookies are present
  useEffect(() => {
    if (!videoId || !cookiesValid) {
      // A request still in flight belongs to a link that is gone; drop it.
      fetchSeq.current++;
      setGuide(false);
      setSubtitleState("idle");
      setSubtitleOptions([]);
      setSubtitleLang("");
      setCaptionOrigCode(null);
      return;
    }

    const seq = ++fetchSeq.current;
    setGuide(false);
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

        setSubtitleOptions(options);
        setCaptionOrigCode(result.captionOrigCode ?? null);

        // Prefer the original-language track (genuine ASR, best transcript and
        // the source of word-level caption timing); fall back to id, then first.
        const preferred =
          (result.captionOrigCode ? options.find((o) => o.code === result.captionOrigCode) : undefined) ??
          options.find((o) => o.code === "id") ??
          options[0];
        setSubtitleLang(`${preferred.code}:${preferred.type}`);
        setSubtitleState("loaded");
        setGuide(true);
      })
      .catch((err) => {
        if (seq !== fetchSeq.current) return;
        console.error("Failed to fetch subtitles", err);
        const detail =
          err instanceof Error ? err.message : typeof err === "string" ? err : JSON.stringify(err, null, 2);
        setSubtitleState("error");
        // Shown as technical detail under the translated status line, so no fallback text.
        setSubtitleError(detail);
      });
  }, [videoId, cookiesValid, url]);

  const subtitlesReady = subtitleState === "loaded" && subtitleLang !== "";
  const isValid = !!videoId && cookiesValid && subtitlesReady;
  const trimmedDirection = userDirection.trim();
  const subtitleCode = subtitleLang.split(":")[0];

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

  // Stop waiting for the subtitle list: forget the request and the link.
  const cancelSubtitles = useCallback(() => {
    fetchSeq.current++;
    setUrl("");
  }, []);

  const handleStart = () => {
    setGuide(false);
    if (!cookiesValid) {
      setShowCookiesDialog(true);
      return;
    }
    if (!isValid) return;
    if (!configLoaded) return;

    // One check for both sources, balance included: a run that dies halfway
    // through because the wallet was already empty wastes the download too.
    const blocker = aiBlocker(config.ai, {
      activated,
      account,
      inappSupported: inappSupported(appInfo),
    });
    if (blocker) {
      toast.error(aiBlockerText(t, blocker));
      navigate("/ai-models");
      return;
    }

    start({
      url,
      numClips: clipCount,
      subtitleLanguage: subtitleCode,
      userDirection: trimmedDirection || undefined,
      outputLanguage,
      ai: buildAIRequest(config.ai),
    });
    navigate("/processing");
  };

  const sortedLanguages = [...OUTPUT_LANGUAGES].sort((a, b) =>
    languageName(a.code).localeCompare(languageName(b.code)),
  );

  const autoName = subtitleCode ? languageName(subtitleCode.replace(/-orig$/, "")) : null;

  const subtitleGroups: ComboboxGroup[] = (() => {
    const option = (o: SubtitleOption) => ({
      value: `${o.code}:${o.type}`,
      label: languageName(o.code.replace(/-orig$/, ""), o.name),
    });
    const original = subtitleOptions.filter((o) => o.code.endsWith("-orig"));
    const manual = subtitleOptions.filter((o) => o.type === "manual" && !o.code.endsWith("-orig"));
    const auto = subtitleOptions
      .filter((o) => o.type === "auto" && !o.code.endsWith("-orig"))
      .map(option)
      .sort((a, b) => a.label.localeCompare(b.label));
    return [
      { label: t("create.picker.groupOriginal"), options: original.map(option) },
      { label: t("create.picker.groupManual"), options: manual.map(option) },
      { label: t("create.picker.groupAuto"), options: auto },
    ].filter((g) => g.options.length > 0);
  })();

  const outputGroups: ComboboxGroup[] = [
    {
      options: [
        {
          value: AUTO_LANGUAGE,
          label: autoName ? t("create.output.autoNamed", { name: autoName }) : t("create.output.auto"),
          short: t("create.output.auto"),
        },
        ...sortedLanguages.map((lang) => ({ value: lang.code, label: languageName(lang.code) })),
      ],
    },
  ];

  const hasVideo = !!videoId;
  const subtitleStatusKey =
    subtitleState === "loaded"
      ? captionOrigCode
        ? "create.status.subtitleOk"
        : "create.status.subtitleNoCaption"
      : subtitleState === "loading"
        ? "create.status.subtitleLoading"
        : subtitleState === "empty"
          ? "create.status.subtitleNone"
          : "create.status.subtitleError";

  return (
    <div
      className={cn(
        "flex flex-col items-center py-6",
        hasVideo ? "justify-start" : "min-h-[calc(100vh-11rem)] justify-center",
      )}
    >
      <div className="w-full max-w-[760px]">
        {/* Identity leads the empty screen; once a video is in, it steps back
            so the video becomes the subject. */}
        <div className="text-center">
          <h1>
            <Wordmark className={hasVideo ? "text-3xl" : "text-5xl sm:text-6xl"} />
          </h1>
          {!hasVideo && (
            <p className="mx-auto mt-4 max-w-md text-lg text-[var(--color-text-secondary)] leading-relaxed">
              {t("create.tagline")}
            </p>
          )}
        </div>

        <form
          className={hasVideo ? "mt-6" : "mt-10"}
          onSubmit={(e) => {
            e.preventDefault();
            handleStart();
          }}
        >
          {/* The link */}
          <div className="flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-primary)] py-2 pl-5 pr-2 focus-within:ring-2 focus-within:ring-[var(--color-border-focus)] focus-within:ring-offset-2 focus-within:ring-offset-[var(--color-bg-secondary)]">
            <Link2 aria-hidden className="h-5 w-5 shrink-0 text-[var(--color-text-muted)]" />
            <label htmlFor="create-url" className="sr-only">
              {t("create.urlLabel")}
            </label>
            <input
              id="create-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t("create.urlPlaceholder")}
              autoComplete="off"
              spellCheck={false}
              className="h-11 min-w-0 flex-1 bg-transparent text-base text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none"
            />
            <button type="button" onClick={handlePaste} className={cn(chip, "shrink-0")}>
              {t("create.paste")}
            </button>
          </div>

          {!hasVideo && (
            <div className="mt-4 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-sm text-[var(--color-text-muted)]">
              <p>{t("create.why.noUrl")}</p>
              {!cookiesValid && (
                <button
                  type="button"
                  onClick={() => setShowCookiesDialog(true)}
                  className="inline-flex min-h-11 items-center font-medium text-[var(--color-warning)] underline underline-offset-4 cursor-pointer"
                >
                  {t("create.cookies.missing")}
                </button>
              )}
            </div>
          )}

          {hasVideo && (
            <>
              {/* The video, and whether it is ready */}
              <div className="mt-6 flex gap-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-3">
                {thumbnailUrl && (
                  <img
                    src={thumbnailUrl}
                    alt={t("create.thumbnailAlt")}
                    className="aspect-video w-40 shrink-0 rounded-[var(--radius-sm)] object-cover sm:w-48"
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.visibility = "hidden";
                    }}
                  />
                )}
                <div className="min-w-0 flex-1 py-0.5">
                  <p className="line-clamp-2 text-base font-semibold text-[var(--color-text-primary)] leading-snug">
                    {videoInfo === "loading" ? t("create.video.loading") : videoInfo?.title || t("create.video.untitled")}
                  </p>
                  {videoInfo && videoInfo !== "loading" && videoInfo.channel && (
                    <p className="mt-0.5 truncate text-sm text-[var(--color-text-secondary)]">{videoInfo.channel}</p>
                  )}
                  <ul aria-live="polite" className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-sm">
                    <li>
                      <button
                        type="button"
                        onClick={() => setShowCookiesDialog(true)}
                        className="inline-flex items-center gap-1.5 cursor-pointer underline-offset-4 hover:underline"
                      >
                        <StatusDot tone={cookiesValid ? "ok" : "warn"} />
                        <span className={cookiesValid ? "text-[var(--color-text-secondary)]" : "text-[var(--color-warning)]"}>
                          {cookiesValid ? t("create.cookies.ok") : t("create.cookies.missing")}
                        </span>
                      </button>
                    </li>
                    {cookiesValid && subtitleState !== "idle" && (
                      <li className="inline-flex items-center gap-1.5">
                        <StatusDot
                          tone={
                            subtitleState === "loading"
                              ? "wait"
                              : subtitleState === "loaded" && captionOrigCode
                                ? "ok"
                                : "warn"
                          }
                        />
                        <span
                          className={
                            subtitleState === "empty" || subtitleState === "error"
                              ? "text-[var(--color-warning)]"
                              : "text-[var(--color-text-secondary)]"
                          }
                        >
                          {t(subtitleStatusKey, { name: autoName ?? "" })}
                        </span>
                      </li>
                    )}
                  </ul>
                  {subtitleState === "error" && subtitleError && (
                    <p className="mt-2 max-h-24 overflow-y-auto whitespace-pre-line font-mono text-xs text-[var(--color-text-muted)]">
                      {subtitleError}
                    </p>
                  )}
                </div>
              </div>

              {/* The options, each named */}
              <div className="mt-6 grid grid-cols-2 gap-x-3 gap-y-4 lg:grid-cols-4">
                <Field label={t("create.field.subtitle")} hint={guide ? t("create.field.subtitleHint") : undefined} help={t("create.help.subtitle")}>
                  <div className={cn("rounded-full", guide && "motion-safe:animate-[cuplik-attention_1.4s_ease-out_2]")}>
                    <Combobox
                      label={t("create.field.subtitle")}
                      value={subtitleLang}
                      groups={subtitleGroups}
                      onChange={setSubtitleLang}
                      onOpenChange={(open) => open && setGuide(false)}
                      disabled={subtitleState !== "loaded"}
                      placeholder={t(`create.subtitle.${subtitleState === "loaded" ? "idle" : subtitleState}`)}
                      searchPlaceholder={t("create.picker.search")}
                      emptyText={t("create.picker.empty")}
                      triggerClassName={cn(chip, "w-full justify-between", guide && "border-[var(--color-accent)]/70")}
                    />
                  </div>
                </Field>

                <Field label={t("create.field.output")} help={t("create.help.output")}>
                  <Combobox
                    label={t("create.field.output")}
                    value={outputLanguage}
                    groups={outputGroups}
                    onChange={setOutputLanguage}
                    placeholder={t("create.output.auto")}
                    searchPlaceholder={t("create.picker.search")}
                    emptyText={t("create.picker.empty")}
                    triggerClassName={cn(chip, "w-full justify-between")}
                  />
                </Field>

                <Field label={t("create.field.clips")} help={t("create.help.clips")}>
                  <div
                    role="group"
                    aria-label={t("create.field.clips")}
                    className={cn(chip, "w-full justify-between gap-0 px-1 hover:bg-[var(--color-bg-primary)]")}
                  >
                    <StepButton
                      ariaLabel={t("create.clips.decrease")}
                      disabled={clipCount <= MIN_CLIPS}
                      onClick={() => setClipCount((n) => Math.max(MIN_CLIPS, n - 1))}
                    >
                      <Minus aria-hidden className="h-4 w-4" />
                    </StepButton>
                    <span aria-live="polite" className="px-1 text-center tabular-nums">
                      {t("create.clips.count", { count: clipCount })}
                    </span>
                    <StepButton
                      ariaLabel={t("create.clips.increase")}
                      disabled={clipCount >= MAX_CLIPS}
                      onClick={() => setClipCount((n) => Math.min(MAX_CLIPS, n + 1))}
                    >
                      <Plus aria-hidden className="h-4 w-4" />
                    </StepButton>
                  </div>
                </Field>

                <Field label={t("create.field.direction")} help={t("create.help.direction")}>
                  <DirectionChip value={userDirection} onChange={setUserDirection} onExample={addExample} />
                </Field>
              </div>

              <div className="mt-8 flex justify-end">
                <Button
                  type="submit"
                  size="lg"
                  disabled={!isValid}
                  className="h-12 w-full gap-2 rounded-full px-7 text-base font-bold sm:w-auto"
                >
                  {t("create.cta")}
                  {/* The arrow says the next screen follows; it is on this button only. */}
                  <ArrowRight aria-hidden className="h-5 w-5" />
                </Button>
              </div>
            </>
          )}
        </form>

        <BlockingProgress
          open={subtitleState === "loading"}
          title={t("create.loading.title")}
          body={t("create.loading.body")}
          elapsedLabel={(count) => t("create.loading.elapsed", { count })}
          cancelLabel={t("create.loading.cancel")}
          onCancel={cancelSubtitles}
        />
      </div>
      {/* Over the page rather than in place of it, so the user keeps their place. */}
      {showCookiesDialog && (
        <CookiesDialog
          onDone={(valid) => {
            setShowCookiesDialog(false);
            if (valid) {
              checkCookies();
              toast.success(t("create.cookies.ready"));
            }
          }}
        />
      )}
    </div>
  );
}

/**
 * A named control: small label above, an info button that explains it on
 * click, and an optional hint beside the label.
 */
function Field({
  label,
  help,
  hint,
  children,
}: {
  label: string;
  help: string;
  hint?: string;
  children: React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className="min-w-0">
      <div className="mb-1.5 flex items-center gap-1 px-1 text-xs font-medium text-[var(--color-text-muted)]">
        <span>{label}</span>
        <Popover>
          <PopoverTrigger
            aria-label={t("create.help.open", { field: label })}
            className="inline-flex h-6 w-6 items-center justify-center rounded-full text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] data-[state=open]:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
          >
            <Info aria-hidden className="h-3.5 w-3.5" />
          </PopoverTrigger>
          <PopoverContent align="start" className="w-[min(300px,calc(100vw-2rem))]">
            <p className="text-sm font-semibold text-[var(--color-text-primary)]">{label}</p>
            <p className="mt-1.5 text-sm text-[var(--color-text-secondary)] leading-relaxed">{help}</p>
          </PopoverContent>
        </Popover>
        {hint && <span className="ml-1 font-normal text-[var(--color-text-secondary)]">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

/** Ready, waiting, or needs attention, as a small dot beside a status line. */
function StatusDot({ tone }: { tone: "ok" | "wait" | "warn" }) {
  return (
    <span
      aria-hidden
      className={cn(
        "h-2 w-2 shrink-0 rounded-full",
        tone === "ok" && "bg-[var(--color-success)]",
        tone === "warn" && "bg-[var(--color-warning)]",
        tone === "wait" && "bg-[var(--color-text-muted)] motion-safe:animate-pulse",
      )}
    />
  );
}

function StepButton({
  ariaLabel,
  disabled,
  onClick,
  children,
}: {
  ariaLabel: string;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={onClick}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:pointer-events-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
    >
      {children}
    </button>
  );
}

/** Optional steer for the AI: a time range, a topic, things to avoid. */
function DirectionChip({
  value,
  onChange,
  onExample,
}: {
  value: string;
  onChange: (value: string) => void;
  onExample: (text: string) => void;
}) {
  const { t } = useTranslation();
  const set = value.trim() !== "";
  return (
    <Popover>
      <PopoverTrigger className={cn(chip, "w-full justify-between cursor-pointer", set && "border-[var(--color-accent)]/60")}>
        {set && <span aria-hidden className="h-2 w-2 rounded-full bg-[var(--color-accent)]" />}
        {set ? t("create.direction.chipSet") : t("create.direction.chip")}
        <ChevronDown aria-hidden className="h-4 w-4 text-[var(--color-text-muted)]" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[min(420px,calc(100vw-2rem))]">
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("create.direction.help")}</p>
        <label className="sr-only" htmlFor="create-direction">
          {t("create.direction.chip")}
        </label>
        <textarea
          id="create-direction"
          value={value}
          onChange={(e) => onChange(e.target.value.slice(0, DIRECTION_MAX))}
          maxLength={DIRECTION_MAX}
          placeholder={t("create.direction.placeholder")}
          className="mt-3 min-h-[110px] w-full resize-y rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] px-3 py-2 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)]"
        />
        <div className="mt-1 flex items-center justify-between">
          <button
            type="button"
            onClick={() => onChange("")}
            disabled={!set}
            className="inline-flex min-h-9 items-center text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
          >
            {t("create.direction.clear")}
          </button>
          <span className="text-xs tabular-nums text-[var(--color-text-muted)]">
            {value.length}/{DIRECTION_MAX}
          </span>
        </div>
        <p className="mt-3 text-xs text-[var(--color-text-muted)]">{t("create.direction.examples")}</p>
        <div className="mt-2 flex flex-col gap-1.5">
          {EXAMPLE_KEYS.map((key) => {
            const text = t(`create.direction.exampleItems.${key}`);
            return (
              <button
                key={key}
                type="button"
                onClick={() => onExample(text)}
                className="rounded-[var(--radius-sm)] border border-[var(--color-border-light)] bg-[var(--color-bg-primary)] px-3 py-2 text-left text-xs text-[var(--color-text-secondary)] hover:border-[var(--color-border)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
              >
                {text}
              </button>
            );
          })}
        </div>
      </PopoverContent>
    </Popover>
  );
}
