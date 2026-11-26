import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { useConfigStore } from "@/stores/configStore";
import type { CreditWatermarkSettings } from "@/hooks/appConfig";
import { cn } from "@/lib/utils";

const FRAME_W = 270;
const FRAME_H = 480;
// ffmpeg draws the text at fontSize pixels on a 1080x1920 clip, so the preview
// scales it down by the same ratio as the frame.
const OUT_W = 1080;
const OUT_H = 1920;
const PREVIEW_RATIO = FRAME_H / OUT_H;
const MARGIN_X = 0.03;
const MARGIN_Y = (MARGIN_X * OUT_W) / OUT_H;
const HEX = /^#[0-9a-fA-F]{6}$/;

const PRESETS = [
  { id: "topLeft", h: "left", v: "top" },
  { id: "topCenter", h: "center", v: "top" },
  { id: "topRight", h: "right", v: "top" },
  { id: "bottomLeft", h: "left", v: "bottom" },
  { id: "bottomCenter", h: "center", v: "bottom" },
  { id: "bottomRight", h: "right", v: "bottom" },
] as const;

type Preset = (typeof PRESETS)[number];

const clamp01 = (n: number) => Math.min(1, Math.max(0, n));
const round3 = (n: number) => Math.round(n * 1000) / 1000;

export function CreditWatermarkSettingsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { config, loaded, load, setCreditWatermark } = useConfigStore();
  const switchId = useId();
  const textId = useId();
  const hexId = useId();

  const [enabled, setEnabled] = useState(false);
  const [text, setText] = useState("");
  const [color, setColor] = useState("#FFFFFF");
  const [fontSize, setFontSize] = useState(24);
  const [opacity, setOpacity] = useState(0.7);
  const [posX, setPosX] = useState(0.03);
  const [posY, setPosY] = useState(0.92);
  const [box, setBox] = useState({ w: 0, h: 0 });
  const [saving, setSaving] = useState(false);

  const frameRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ dx: number; dy: number } | null>(null);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!loaded) return;
    const c = config.creditWatermark;
    setEnabled(c.enabled);
    setText(c.text);
    setColor(c.color);
    setFontSize(c.fontSize);
    setOpacity(c.opacity);
    setPosX(c.positionX);
    setPosY(c.positionY);
  }, [loaded, config.creditWatermark]);

  // Corner presets and drag limits need the text's size as a fraction of the frame.
  useLayoutEffect(() => {
    const el = textRef.current;
    if (!el) return;
    setBox({ w: el.offsetWidth / FRAME_W, h: el.offsetHeight / FRAME_H });
  }, [text, fontSize, loaded]);

  const colorValid = HEX.test(color);
  const showsPlaceholder = text.includes("{channel}");

  const presetPosition = (p: Preset) => ({
    x: clamp01(p.h === "left" ? MARGIN_X : p.h === "right" ? 1 - MARGIN_X - box.w : 0.5 - box.w / 2),
    y: clamp01(p.v === "top" ? MARGIN_Y : 1 - MARGIN_Y - box.h),
  });

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!enabled) return;
      const frame = frameRef.current;
      if (!frame) return;
      const rect = frame.getBoundingClientRect();
      dragState.current = {
        dx: e.clientX - rect.left - posX * FRAME_W,
        dy: e.clientY - rect.top - posY * FRAME_H,
      };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [enabled, posX, posY],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragState.current) return;
      const frame = frameRef.current;
      if (!frame) return;
      const rect = frame.getBoundingClientRect();
      const x = (e.clientX - rect.left - dragState.current.dx) / FRAME_W;
      const y = (e.clientY - rect.top - dragState.current.dy) / FRAME_H;
      setPosX(round3(Math.min(Math.max(0, 1 - box.w), Math.max(0, x))));
      setPosY(round3(Math.min(Math.max(0, 1 - box.h), Math.max(0, y))));
    },
    [box],
  );

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    dragState.current = null;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  }, []);

  const handleSave = async () => {
    const trimmed = text.trim();
    if (enabled && !trimmed) {
      toast.error(t("creditSettings.errors.needText"));
      return;
    }
    if (!colorValid) {
      toast.error(t("creditSettings.errors.badColor"));
      return;
    }
    setSaving(true);
    const next: CreditWatermarkSettings = {
      enabled,
      text: trimmed,
      color: color.toUpperCase(),
      fontSize,
      opacity,
      positionX: posX,
      positionY: posY,
    };
    try {
      await setCreditWatermark(next);
      toast.success(t("creditSettings.saved"));
      navigate("/settings");
    } catch (err) {
      toast.error(t("creditSettings.saveFailed", { reason: String(err) }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl py-4">
      <button
        type="button"
        onClick={() => navigate("/settings")}
        className="-ml-2 inline-flex min-h-10 items-center gap-1.5 rounded-full px-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
      >
        <ArrowLeft aria-hidden className="h-4 w-4" />
        {t("creditSettings.back")}
      </button>

      <h1 className="mt-4 text-2xl font-bold text-[var(--color-text-primary)]">{t("creditSettings.title")}</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("creditSettings.subtitle")}</p>

      {!loaded ? (
        <div className="mt-9 flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          {t("creditSettings.loading")}
        </div>
      ) : (
        <div className="mt-8 grid gap-8 md:grid-cols-[270px_minmax(0,1fr)] md:gap-10">
          {/* Preview */}
          <div className="md:sticky md:top-4 md:self-start">
            <p className="text-sm font-medium text-[var(--color-text-primary)]">{t("creditSettings.preview.label")}</p>
            <div
              ref={frameRef}
              role="img"
              aria-label={t("creditSettings.preview.aria")}
              className="relative mt-3 mx-auto overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-gradient-to-b from-[var(--color-bg-card)] to-black select-none touch-none"
              style={{ width: FRAME_W, height: FRAME_H }}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
            >
              <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-xs text-[var(--color-text-muted)]">
                {t("creditSettings.preview.frame")}
              </span>
              <div
                ref={textRef}
                onPointerDown={onPointerDown}
                className={cn(
                  "absolute whitespace-pre font-sans leading-none",
                  enabled ? "cursor-grab active:cursor-grabbing" : "grayscale",
                )}
                style={{
                  left: posX * FRAME_W,
                  top: posY * FRAME_H,
                  color: colorValid ? color : "#FFFFFF",
                  fontSize: fontSize * PREVIEW_RATIO,
                  opacity: enabled ? opacity : opacity * 0.35,
                  textShadow: "0.5px 0.5px 0.5px rgba(0,0,0,0.5)",
                }}
              >
                {text.trim() || t("creditSettings.text.placeholder")}
              </div>
            </div>
            <p className="mt-2 text-center text-xs text-[var(--color-text-muted)]">
              {enabled ? t("creditSettings.preview.hint") : t("creditSettings.preview.off")}
            </p>
          </div>

          {/* Controls */}
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4">
              <div className="min-w-0">
                <label htmlFor={switchId} className="text-sm font-medium text-[var(--color-text-primary)] cursor-pointer">
                  {t("creditSettings.enable.title")}
                </label>
                <p className="mt-0.5 text-xs text-[var(--color-text-muted)] leading-relaxed">{t("creditSettings.enable.body")}</p>
              </div>
              <Switch id={switchId} checked={enabled} onCheckedChange={setEnabled} />
            </div>

            <fieldset disabled={!enabled} className={cn("min-w-0 transition-opacity", !enabled && "opacity-50")}>
              <Section title={t("creditSettings.text.title")} body={t("creditSettings.text.body")}>
                <label htmlFor={textId} className="text-sm font-medium text-[var(--color-text-primary)]">
                  {t("creditSettings.text.label")}
                </label>
                <Input
                  id={textId}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={t("creditSettings.text.placeholder")}
                  className="mt-2"
                />
                {showsPlaceholder && (
                  <p className="mt-2 text-xs text-[var(--color-text-muted)] leading-relaxed">
                    {t("creditSettings.text.placeholderWarning")}
                  </p>
                )}
              </Section>

              <Section title={t("creditSettings.position.title")} body={t("creditSettings.position.body")}>
                <PositionPresets
                  label={t("creditSettings.position.presetsAria")}
                  disabled={!enabled}
                  isActive={(p) => {
                    const pos = presetPosition(p);
                    return Math.abs(pos.x - posX) < 0.006 && Math.abs(pos.y - posY) < 0.006;
                  }}
                  onPick={(p) => {
                    const pos = presetPosition(p);
                    setPosX(round3(pos.x));
                    setPosY(round3(pos.y));
                  }}
                  name={(p) => t(`creditSettings.position.presets.${p.id}`)}
                />
                <div className="mt-5 space-y-5">
                  <SliderRow
                    label={t("creditSettings.position.x")}
                    value={t("creditSettings.position.value", { pct: Math.round(posX * 100) })}
                    disabled={!enabled}
                    slider={{ value: [posX], onValueChange: (v) => setPosX(v[0]), min: 0, max: 1, step: 0.01 }}
                  />
                  <SliderRow
                    label={t("creditSettings.position.y")}
                    value={t("creditSettings.position.value", { pct: Math.round(posY * 100) })}
                    disabled={!enabled}
                    slider={{ value: [posY], onValueChange: (v) => setPosY(v[0]), min: 0, max: 1, step: 0.01 }}
                  />
                </div>
              </Section>

              <Section title={t("creditSettings.look.title")}>
                <div className="space-y-5">
                  <div>
                    <label htmlFor={hexId} className="text-sm font-medium text-[var(--color-text-primary)]">
                      {t("creditSettings.look.color")}
                    </label>
                    <div className="mt-2 flex items-center gap-3">
                      <input
                        type="color"
                        aria-label={t("creditSettings.look.colorPicker")}
                        value={colorValid ? color.toLowerCase() : "#ffffff"}
                        onChange={(e) => setColor(e.target.value.toUpperCase())}
                        className="h-10 w-10 shrink-0 cursor-pointer appearance-none rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] p-1 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] [&::-webkit-color-swatch-wrapper]:p-0 [&::-webkit-color-swatch]:rounded-[4px] [&::-webkit-color-swatch]:border-none"
                      />
                      <Input
                        id={hexId}
                        value={color}
                        onChange={(e) => setColor(e.target.value.trim())}
                        aria-invalid={!colorValid}
                        aria-describedby={colorValid ? undefined : `${hexId}-error`}
                        maxLength={7}
                        spellCheck={false}
                        className={cn("w-32 font-mono", !colorValid && "border-[var(--color-error)]")}
                      />
                    </div>
                    {!colorValid && (
                      <p id={`${hexId}-error`} className="mt-2 text-xs text-[var(--color-error)]">
                        {t("creditSettings.look.colorInvalid")}
                      </p>
                    )}
                  </div>
                  <SliderRow
                    label={t("creditSettings.look.fontSize")}
                    value={t("creditSettings.look.fontSizeValue", { px: fontSize })}
                    disabled={!enabled}
                    slider={{ value: [fontSize], onValueChange: (v) => setFontSize(v[0]), min: 12, max: 72, step: 1 }}
                  />
                  <SliderRow
                    label={t("creditSettings.look.opacity")}
                    value={`${Math.round(opacity * 100)}%`}
                    disabled={!enabled}
                    slider={{ value: [opacity], onValueChange: (v) => setOpacity(v[0]), min: 0.1, max: 1, step: 0.05 }}
                  />
                </div>
              </Section>
            </fieldset>

            <div className="mt-8 flex justify-end">
              <Button onClick={handleSave} disabled={saving} className="min-w-32">
                {saving && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
                {saving ? t("creditSettings.saving") : t("creditSettings.save")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ title, body, children }: { title: string; body?: string; children: React.ReactNode }) {
  return (
    <section className="mt-9">
      <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
      {body && <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{body}</p>}
      <div className="mt-3 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4">
        {children}
      </div>
    </section>
  );
}

function SliderRow({
  label,
  value,
  disabled,
  slider,
}: {
  label: string;
  value: string;
  disabled?: boolean;
  slider: React.ComponentProps<typeof Slider>;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const labelId = useId();

  // The shared Slider does not pass labels down to its thumb, which is the
  // element screen readers land on.
  useEffect(() => {
    const thumb = ref.current?.querySelector('[role="slider"]');
    thumb?.setAttribute("aria-labelledby", labelId);
    thumb?.setAttribute("aria-valuetext", value);
  }, [labelId, value]);

  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <span id={labelId} className="text-sm font-medium text-[var(--color-text-primary)]">
          {label}
        </span>
        <span className="text-sm tabular-nums text-[var(--color-text-secondary)]">{value}</span>
      </div>
      <Slider ref={ref} {...slider} disabled={disabled} className="mt-3 min-h-6" />
    </div>
  );
}

function PositionPresets({
  label,
  disabled,
  isActive,
  onPick,
  name,
}: {
  label: string;
  disabled?: boolean;
  isActive: (p: Preset) => boolean;
  onPick: (p: Preset) => void;
  name: (p: Preset) => string;
}) {
  return (
    <div role="group" aria-label={label} className="grid grid-cols-3 gap-2">
      {PRESETS.map((p) => {
        const on = isActive(p);
        return (
          <button
            key={p.id}
            type="button"
            aria-pressed={on}
            disabled={disabled}
            onClick={() => onPick(p)}
            className={cn(
              "min-h-10 rounded-[var(--radius-sm)] border px-2 text-xs font-medium transition-colors cursor-pointer disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]",
              on
                ? "border-[var(--color-text-muted)] bg-[var(--color-bg-hover)] text-[var(--color-text-primary)]"
                : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] hover:text-[var(--color-text-primary)]",
            )}
          >
            {name(p)}
          </button>
        );
      })}
    </div>
  );
}
