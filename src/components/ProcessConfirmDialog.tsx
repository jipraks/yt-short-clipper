import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowRight, Check, Maximize2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { useConfigStore } from "@/stores/configStore";
import type { ReframeMode, CenteredBackground } from "@/hooks/processClips";

export type { ProcessOptions } from "@/hooks/processClips";
import type { ProcessOptions } from "@/hooks/processClips";

/** Matches cuplik-panel-out below. */
const EXIT_MS = 160;

const SHAPES: ReframeMode[] = ["face", "centered", "original"];

/** Screenshots of a real render. "original" has none: it is the source frame. */
function sampleFor(mode: ReframeMode, background: CenteredBackground): string | null {
  if (mode === "face") return "/sample-face-tracking.png";
  if (mode === "centered") return background === "blurred" ? "/sample-centered-blur.png" : "/sample-centered-black.png";
  return null;
}

interface ProcessConfirmDialogProps {
  clipCount: number;
  /** Whether the source video has an original subtitle track usable for captions. */
  captionsAvailable?: boolean;
  onConfirm: (options: ProcessOptions) => void;
  onCancel: () => void;
}

/**
 * The last stop before rendering: the video shape on the left with a live
 * example of the result on the right, then the overlays. An overlay that has
 * nothing to show yet (no logo, no credit text) cannot be switched on, and
 * says where to set it up, instead of silently rendering without it.
 */
export function ProcessConfirmDialog({ clipCount, captionsAvailable = true, onConfirm, onCancel }: ProcessConfirmDialogProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { config } = useConfigStore();

  const hasLogo = config.watermark.imagePath.trim() !== "";
  const creditText = config.creditWatermark.text.trim();
  const hasCredit = creditText !== "";

  const [addCaptions, setAddCaptions] = useState(captionsAvailable);
  const [addHook, setAddHook] = useState(true);
  const [addWatermark, setAddWatermark] = useState(config.watermark.enabled && hasLogo);
  const [addCreditWatermark, setAddCreditWatermark] = useState(config.creditWatermark.enabled && hasCredit);
  const [reframeMode, setReframeMode] = useState<ReframeMode>("face");
  const [centeredBackground, setCenteredBackground] = useState<CenteredBackground>("black");
  const [zoomed, setZoomed] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const close = useCallback(
    (then?: () => void) => {
      if (leaving) return;
      setLeaving(true);
      setTimeout(() => {
        onCancel();
        then?.();
      }, EXIT_MS);
    },
    [leaving, onCancel],
  );

  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.preventDefault();
      if (zoomed) setZoomed(false);
      else close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoomed, close]);

  const sample = sampleFor(reframeMode, centeredBackground);

  const confirm = () => {
    onConfirm({
      addCaptions: addCaptions && captionsAvailable,
      addHook,
      addWatermark: addWatermark && hasLogo,
      addCreditWatermark: addCreditWatermark && hasCredit,
      reframeMode,
      centeredBackground,
    });
  };

  // Arrow keys move between the shapes, like any radio group.
  const onShapeKey = (e: React.KeyboardEvent, index: number) => {
    const step = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    e.preventDefault();
    const next = SHAPES[(index + step + SHAPES.length) % SHAPES.length];
    setReframeMode(next);
    document.getElementById(`render-shape-${next}`)?.focus();
  };

  return (
    <>
      <div
        className={`fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 ${
          leaving
            ? "pointer-events-none motion-safe:animate-[cuplik-overlay-out_160ms_ease-in_forwards]"
            : "motion-safe:animate-[cuplik-overlay-in_200ms_ease-out]"
        }`}
        onClick={(e) => {
          if (e.target === e.currentTarget) close();
        }}
      >
        <div
          ref={panelRef}
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-labelledby="render-dialog-title"
          aria-describedby="render-dialog-subtitle"
          className={`flex max-h-[min(94vh,780px)] w-full max-w-3xl flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-card)] shadow-[var(--shadow-lg)] outline-none ${
            leaving
              ? "motion-safe:animate-[cuplik-panel-out_160ms_ease-in_forwards]"
              : "motion-safe:animate-[cuplik-panel-in_250ms_cubic-bezier(0.16,1,0.3,1)]"
          }`}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-4 px-6 pt-6">
            <div className="min-w-0">
              <h2 id="render-dialog-title" className="text-xl font-bold text-[var(--color-text-primary)]">
                {t("renderDialog.title", { count: clipCount })}
              </h2>
              <p id="render-dialog-subtitle" className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {t("renderDialog.subtitle")}
              </p>
            </div>
            <button
              type="button"
              onClick={() => close()}
              aria-label={t("renderDialog.close")}
              className="-mr-2 -mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
            >
              <X aria-hidden className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
            <div className="grid gap-6 md:grid-cols-[1fr_220px]">
              <div className="min-w-0">
                {/* Shape */}
                <section aria-labelledby="render-shape-label">
                  <h3 id="render-shape-label" className="mb-2.5 text-xs font-medium text-[var(--color-text-muted)]">
                    {t("renderDialog.shape.label")}
                  </h3>
                  <div role="radiogroup" aria-labelledby="render-shape-label" className="grid gap-2">
                    {SHAPES.map((mode, i) => {
                      const selected = reframeMode === mode;
                      return (
                        <button
                          key={mode}
                          id={`render-shape-${mode}`}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          tabIndex={selected ? 0 : -1}
                          onClick={() => setReframeMode(mode)}
                          onKeyDown={(e) => onShapeKey(e, i)}
                          className={`flex items-center gap-3.5 rounded-[var(--radius)] border px-3 py-2.5 text-left transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] ${
                            selected
                              ? "border-[var(--color-accent)] bg-[var(--color-bg-hover)]"
                              : "border-[var(--color-border)] hover:border-[var(--color-text-muted)]"
                          }`}
                        >
                          <ShapeGlyph mode={mode} />
                          <span className="min-w-0 flex-1">
                            <span className="flex flex-wrap items-baseline gap-x-2">
                              <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                                {t(`renderDialog.shape.${mode}.title`)}
                              </span>
                              <span className="text-xs text-[var(--color-text-muted)]">
                                {t(`renderDialog.shape.${mode}.speed`)}
                              </span>
                            </span>
                            <span className="mt-0.5 block text-xs text-[var(--color-text-secondary)] leading-relaxed">
                              {t(`renderDialog.shape.${mode}.body`)}
                            </span>
                          </span>
                          <span
                            aria-hidden
                            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                              selected
                                ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-[var(--color-bg-primary)]"
                                : "border-[var(--color-border)]"
                            }`}
                          >
                            {selected && <Check className="h-3 w-3" strokeWidth={3} />}
                          </span>
                        </button>
                      );
                    })}
                  </div>

                  {reframeMode === "centered" && (
                    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 px-1">
                      <span id="render-bg-label" className="text-xs text-[var(--color-text-muted)]">
                        {t("renderDialog.background.label")}
                      </span>
                      <div
                        role="radiogroup"
                        aria-labelledby="render-bg-label"
                        className="inline-flex rounded-full border border-[var(--color-border)] p-0.5"
                      >
                        {(["black", "blurred"] as CenteredBackground[]).map((bg) => {
                          const on = centeredBackground === bg;
                          return (
                            <button
                              key={bg}
                              type="button"
                              role="radio"
                              aria-checked={on}
                              onClick={() => setCenteredBackground(bg)}
                              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] ${
                                on
                                  ? "bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
                                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                              }`}
                            >
                              {t(`renderDialog.background.${bg}`)}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </section>

                {/* Overlays */}
                <section aria-labelledby="render-extras-label" className="mt-5">
                  <h3 id="render-extras-label" className="mb-2.5 text-xs font-medium text-[var(--color-text-muted)]">
                    {t("renderDialog.extras.label")}
                  </h3>
                  <div className="grid gap-2">
                    <ExtraRow
                      id="captions"
                      title={t("renderDialog.extras.captions.title")}
                      body={
                        captionsAvailable
                          ? t("renderDialog.extras.captions.body")
                          : t("renderDialog.extras.captions.unavailable")
                      }
                      checked={addCaptions && captionsAvailable}
                      onChange={setAddCaptions}
                      disabled={!captionsAvailable}
                    />
                    <ExtraRow
                      id="hook"
                      title={t("renderDialog.extras.hook.title")}
                      body={t("renderDialog.extras.hook.body")}
                      checked={addHook}
                      onChange={setAddHook}
                      action={{ label: t("renderDialog.extras.edit"), onClick: () => close(() => navigate("/settings/hook-style")) }}
                    />
                    <ExtraRow
                      id="logo"
                      title={t("renderDialog.extras.logo.title")}
                      body={hasLogo ? t("renderDialog.extras.logo.body") : t("renderDialog.extras.logo.missing")}
                      checked={addWatermark && hasLogo}
                      onChange={setAddWatermark}
                      disabled={!hasLogo}
                      action={{
                        label: hasLogo ? t("renderDialog.extras.edit") : t("renderDialog.extras.setUp"),
                        onClick: () => close(() => navigate("/settings/watermark")),
                      }}
                    />
                    <ExtraRow
                      id="credit"
                      title={t("renderDialog.extras.credit.title")}
                      body={
                        hasCredit
                          ? t("renderDialog.extras.credit.body", { text: creditText })
                          : t("renderDialog.extras.credit.missing")
                      }
                      checked={addCreditWatermark && hasCredit}
                      onChange={setAddCreditWatermark}
                      disabled={!hasCredit}
                      action={{
                        label: hasCredit ? t("renderDialog.extras.edit") : t("renderDialog.extras.setUp"),
                        onClick: () => close(() => navigate("/settings/credit")),
                      }}
                    />
                  </div>
                </section>
              </div>

              {/* Example result */}
              <section aria-labelledby="render-preview-label" className="hidden md:block md:sticky md:top-0 md:self-start">
                <h3 id="render-preview-label" className="mb-2.5 text-xs font-medium text-[var(--color-text-muted)]">
                  {t("renderDialog.preview.label")}
                </h3>
                {sample ? (
                  <button
                    type="button"
                    onClick={() => setZoomed(true)}
                    aria-label={t("renderDialog.preview.enlarge")}
                    className="group relative block aspect-[9/16] w-full overflow-hidden rounded-[var(--radius)] border border-[var(--color-border)] bg-black cursor-zoom-in focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
                  >
                    <img
                      key={sample}
                      src={sample}
                      alt=""
                      className="h-full w-full object-cover motion-safe:animate-[cuplik-overlay-in_200ms_ease-out]"
                    />
                    <span className="absolute right-2 top-2 inline-flex h-7 w-7 items-center justify-center rounded-full bg-black/60 text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                      <Maximize2 aria-hidden className="h-3.5 w-3.5" />
                    </span>
                  </button>
                ) : (
                  <div className="flex aspect-[9/16] w-full flex-col items-center justify-center gap-3 rounded-[var(--radius)] border border-dashed border-[var(--color-border)] p-4 text-center">
                    <div className="aspect-video w-full rounded-[var(--radius-sm)] bg-[var(--color-bg-hover)]" />
                    <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
                      {t("renderDialog.preview.originalNote")}
                    </p>
                  </div>
                )}
              </section>
            </div>

          </div>

          {/* Footer */}
          <div className="flex flex-col-reverse gap-2 border-t border-[var(--color-border)] px-6 py-4 sm:flex-row sm:justify-end">
            <Button variant="ghost" onClick={() => close()} className="h-11 px-5">
              {t("renderDialog.cancel")}
            </Button>
            <Button onClick={confirm} disabled={leaving} className="h-11 gap-2 px-6 text-base font-semibold">
              {t("renderDialog.confirm", { count: clipCount })}
              <ArrowRight aria-hidden className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {zoomed && sample && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85 p-6 motion-safe:animate-[cuplik-overlay-in_160ms_ease-out]"
          onClick={() => setZoomed(false)}
        >
          <button
            type="button"
            onClick={() => setZoomed(false)}
            aria-label={t("renderDialog.preview.close")}
            className="absolute right-5 top-5 inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
          >
            <X aria-hidden className="h-5 w-5" />
          </button>
          <img
            src={sample}
            alt={t(`renderDialog.shape.${reframeMode}.title`)}
            className="max-h-full max-w-full rounded-[var(--radius-md)] shadow-2xl motion-safe:animate-[cuplik-panel-in_220ms_cubic-bezier(0.16,1,0.3,1)]"
          />
        </div>
      )}
    </>
  );
}

/** A tiny drawing of the output frame, so the three shapes differ at a glance. */
function ShapeGlyph({ mode }: { mode: ReframeMode }) {
  if (mode === "original") {
    return (
      <span aria-hidden className="flex h-10 w-10 shrink-0 items-center justify-center">
        <span className="h-[22px] w-10 rounded-[4px] border-2 border-[var(--color-text-muted)]" />
      </span>
    );
  }
  return (
    <span aria-hidden className="flex h-10 w-10 shrink-0 items-center justify-center">
      <span className="relative flex h-10 w-[23px] items-center justify-center overflow-hidden rounded-[4px] border-2 border-[var(--color-text-muted)]">
        {mode === "face" ? (
          <span className="flex flex-col items-center">
            <span className="h-2 w-2 rounded-full bg-[var(--color-accent)]" />
            <span className="mt-0.5 h-1.5 w-3.5 rounded-t-full bg-[var(--color-accent)]" />
          </span>
        ) : (
          <span className="h-[9px] w-full bg-[var(--color-text-muted)]" />
        )}
      </span>
    </span>
  );
}

function ExtraRow({
  id,
  title,
  body,
  checked,
  onChange,
  disabled,
  action,
}: {
  id: string;
  title: string;
  body: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  action?: { label: string; onClick: () => void };
}) {
  const switchId = `render-extra-${id}`;
  return (
    <div className="flex items-start gap-3 rounded-[var(--radius)] border border-[var(--color-border)] px-3.5 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <label
            htmlFor={switchId}
            className={`text-sm font-semibold ${
              disabled ? "text-[var(--color-text-muted)]" : "text-[var(--color-text-primary)] cursor-pointer"
            }`}
          >
            {title}
          </label>
          {action && (
            <button
              type="button"
              onClick={action.onClick}
              className="text-xs font-medium text-[var(--color-accent)] hover:underline underline-offset-2 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] rounded-sm"
            >
              {action.label}
            </button>
          )}
        </div>
        <p className="mt-0.5 text-xs text-[var(--color-text-secondary)] leading-relaxed">{body}</p>
      </div>
      <div className="pt-0.5">
        <Switch id={switchId} checked={checked} onCheckedChange={onChange} disabled={disabled} />
      </div>
    </div>
  );
}
