import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Combobox } from "@/components/ui/combobox";
import { listHookFonts, readFontAsBase64, type FontInfo, type HookStyleSettings } from "@/hooks/appConfig";
import { useConfigStore } from "@/stores/configStore";

const CANVAS_W = 288;
const CANVAS_H = 512;
const VIDEO_W = 1080;
const SCALE = CANVAS_W / VIDEO_W;

const DEFAULTS: HookStyleSettings = {
  fontName: "Arial",
  fontPath: "",
  fontSize: 0.054,
  fontColor: "#FFD700",
  bgColor: "#FFFFFF",
  cornerRadius: 0,
  positionX: 0.5,
  positionY: 0.333,
  durationSeconds: 5,
};

const HEX = /^#[0-9a-f]{6}$/i;

/** Accepts "#abc", "abc", "#aabbcc" or "aabbcc"; anything else is null. */
function normalizeHex(raw: string): string | null {
  let v = raw.trim();
  if (!v.startsWith("#")) v = `#${v}`;
  if (/^#[0-9a-f]{3}$/i.test(v)) v = `#${v[1]}${v[1]}${v[2]}${v[2]}${v[3]}${v[3]}`;
  return HEX.test(v) ? v.toUpperCase() : null;
}

/** The renderer upper-cases the hook and breaks it every three words. */
function hookLines(text: string): string[] {
  const words = text.toUpperCase().split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  for (let i = 0; i < words.length; i += 3) lines.push(words.slice(i, i + 3).join(" "));
  return lines;
}

const clamp01 = (n: number) => Math.max(0, Math.min(1, n));

/**
 * The hook text burned over the first seconds of each clip. A 9:16 preview on
 * the left mirrors the renderer's layout (upper case, three words a line, one
 * box per line) and can be dragged; the controls on the right are grouped by
 * what they change.
 */
export function HookStyleSettingsPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { config, loaded, load, setHookStyle } = useConfigStore();

  const [fontName, setFontName] = useState(DEFAULTS.fontName);
  const [fontPath, setFontPath] = useState(DEFAULTS.fontPath);
  const [fontSize, setFontSize] = useState(DEFAULTS.fontSize);
  const [fontColor, setFontColor] = useState(DEFAULTS.fontColor);
  const [bgColor, setBgColor] = useState(DEFAULTS.bgColor);
  const [cornerRadius, setCornerRadius] = useState(DEFAULTS.cornerRadius);
  const [posX, setPosX] = useState(DEFAULTS.positionX);
  const [posY, setPosY] = useState(DEFAULTS.positionY);
  const [durationSeconds, setDurationSeconds] = useState(DEFAULTS.durationSeconds);
  const [saving, setSaving] = useState(false);

  const [fonts, setFonts] = useState<FontInfo[] | null>(null);
  const [fontsFailed, setFontsFailed] = useState(false);
  const [fontUrls, setFontUrls] = useState<Record<string, string>>({});

  const canvasRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ dx: number; dy: number } | null>(null);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!loaded) return;
    const h = config.hookStyle;
    setFontName(h.fontName);
    setFontPath(h.fontPath);
    setFontSize(h.fontSize);
    setFontColor(h.fontColor);
    setBgColor(h.bgColor);
    setCornerRadius(h.cornerRadius);
    setPosX(h.positionX);
    setPosY(h.positionY);
    setDurationSeconds(h.durationSeconds);
  }, [loaded, config.hookStyle]);

  useEffect(() => {
    listHookFonts()
      .then(setFonts)
      .catch((err) => {
        console.error("Failed to list hook fonts", err);
        setFontsFailed(true);
        setFonts([]);
      });
  }, []);

  // A saved font that is no longer installed falls back to the first one found.
  useEffect(() => {
    if (!loaded || !fonts || fonts.length === 0) return;
    if (!fonts.some((f) => f.name === fontName)) {
      setFontName(fonts[0].name);
      setFontPath(fonts[0].path);
    }
  }, [loaded, fonts, fontName]);

  // Only the chosen font is read, so the preview can draw with it.
  useEffect(() => {
    if (!fontPath || fontUrls[fontPath]) return;
    let live = true;
    readFontAsBase64(fontPath)
      .then((url) => live && setFontUrls((m) => ({ ...m, [fontPath]: url })))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [fontPath, fontUrls]);

  const pickFont = (name: string) => {
    setFontName(name);
    const found = fonts?.find((f) => f.name === name);
    if (found) setFontPath(found.path);
  };

  const fontGroups = useMemo(() => {
    if (fonts === null) return [];
    const options = fonts.map((f) => ({ value: f.name, label: f.name }));
    if (fontName && !options.some((o) => o.value === fontName)) options.unshift({ value: fontName, label: fontName });
    return [{ options }];
  }, [fonts, fontName]);

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      drag.current = {
        dx: e.clientX - rect.left - posX * CANVAS_W,
        dy: e.clientY - rect.top - posY * CANVAS_H,
      };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [posX, posY],
  );

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    if (!drag.current || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    setPosX(clamp01((e.clientX - rect.left - drag.current.dx) / CANVAS_W));
    setPosY(clamp01((e.clientY - rect.top - drag.current.dy) / CANVAS_H));
  }, []);

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    drag.current = null;
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await setHookStyle({
        fontName,
        fontPath,
        fontSize,
        fontColor,
        bgColor,
        cornerRadius,
        positionX: posX,
        positionY: posY,
        durationSeconds,
      });
      toast.success(t("hookStyleSettings.saved"));
      navigate("/settings");
    } catch {
      toast.error(t("hookStyleSettings.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const reset = () => {
    setFontName(DEFAULTS.fontName);
    setFontPath(DEFAULTS.fontPath);
    setFontSize(DEFAULTS.fontSize);
    setFontColor(DEFAULTS.fontColor);
    setBgColor(DEFAULTS.bgColor);
    setCornerRadius(DEFAULTS.cornerRadius);
    setPosX(DEFAULTS.positionX);
    setPosY(DEFAULTS.positionY);
    setDurationSeconds(DEFAULTS.durationSeconds);
  };

  const num = (n: number, digits = 0) => n.toLocaleString(i18n.language, { maximumFractionDigits: digits });

  // Same numbers the renderer uses, scaled from 1080 px wide to the preview.
  const videoFontPx = Math.max(20, fontSize * VIDEO_W);
  const previewFontPx = videoFontPx * SCALE;
  const padding = Math.max(10, videoFontPx * 0.22) * SCALE;
  const lineGap = Math.max(6, videoFontPx * 0.25) * SCALE;
  const fontUrl = fontUrls[fontPath];
  const previewFamily = `cuplik-hook-${fontName.replace(/[^a-zA-Z0-9_-]/g, "")}`;
  const lines = hookLines(t("hookStyleSettings.preview.sample"));

  return (
    <div className="mx-auto max-w-4xl py-4">
      {fontUrl && (
        <style>{`@font-face { font-family: "${previewFamily}"; src: url("${fontUrl}"); }`}</style>
      )}

      <button
        type="button"
        onClick={() => navigate("/settings")}
        className="-ml-2 inline-flex min-h-10 items-center gap-1.5 rounded-full px-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
      >
        <ArrowLeft aria-hidden className="h-4 w-4" />
        {t("hookStyleSettings.back")}
      </button>

      <h1 className="mt-4 text-2xl font-bold text-[var(--color-text-primary)]">{t("hookStyleSettings.title")}</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("hookStyleSettings.subtitle")}</p>

      <div className="mt-8 grid gap-8 md:grid-cols-[minmax(0,288px)_minmax(0,1fr)]">
        {/* Preview */}
        <div className="md:sticky md:top-4 md:self-start">
          <div
            ref={canvasRef}
            role="img"
            aria-label={t("hookStyleSettings.preview.label")}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerUp}
            className="relative mx-auto touch-none select-none overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[linear-gradient(180deg,#24242b_0%,#141418_100%)] cursor-grab active:cursor-grabbing"
            style={{ width: CANVAS_W, height: CANVAS_H }}
          >
            <div
              className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
              style={{ left: posX * CANVAS_W, top: posY * CANVAS_H, gap: lineGap }}
            >
              {lines.map((line, i) => (
                <span
                  key={i}
                  className="whitespace-nowrap font-bold leading-none"
                  style={{
                    padding,
                    backgroundColor: bgColor,
                    color: fontColor,
                    borderRadius: cornerRadius * SCALE,
                    fontSize: previewFontPx,
                    fontFamily: fontUrl ? `"${previewFamily}", sans-serif` : `"${fontName}", sans-serif`,
                  }}
                >
                  {line}
                </span>
              ))}
            </div>
          </div>
          <p className="mt-3 text-center text-xs text-[var(--color-text-muted)]">{t("hookStyleSettings.preview.hint")}</p>
        </div>

        {/* Controls */}
        <div className="min-w-0">
          <Group title={t("hookStyleSettings.text.title")} body={t("hookStyleSettings.text.body")} first>
            <div className="space-y-1.5">
              <p className="text-sm font-medium text-[var(--color-text-primary)]">{t("hookStyleSettings.text.font")}</p>
              <Combobox
                label={t("hookStyleSettings.text.font")}
                value={fontName}
                groups={fontGroups}
                onChange={pickFont}
                disabled={fonts === null}
                placeholder={fonts === null ? t("hookStyleSettings.text.fontLoading") : fontName}
                searchPlaceholder={t("hookStyleSettings.text.fontSearch")}
                emptyText={t("hookStyleSettings.text.fontEmpty")}
                triggerClassName="inline-flex h-11 w-full items-center justify-between gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-bg-primary)] px-4 text-sm text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-bg-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)] disabled:opacity-60"
              />
              {fontsFailed && <p className="text-xs text-[var(--color-warning)]">{t("hookStyleSettings.text.fontsFailed")}</p>}
            </div>
            <SliderField
              label={t("hookStyleSettings.text.size")}
              readout={t("hookStyleSettings.text.sizeValue", { value: num(fontSize * 100, 1) })}
              value={fontSize}
              onChange={setFontSize}
              min={0.025}
              max={0.1}
              step={0.0025}
            />
            <ColorField label={t("hookStyleSettings.text.color")} value={fontColor} onChange={setFontColor} />
          </Group>

          <Group title={t("hookStyleSettings.box.title")} body={t("hookStyleSettings.box.body")}>
            <ColorField label={t("hookStyleSettings.box.background")} value={bgColor} onChange={setBgColor} />
            <SliderField
              label={t("hookStyleSettings.box.radius")}
              readout={
                cornerRadius === 0
                  ? t("hookStyleSettings.box.radiusSharp")
                  : t("hookStyleSettings.box.radiusValue", { value: num(cornerRadius) })
              }
              value={cornerRadius}
              onChange={setCornerRadius}
              min={0}
              max={80}
              step={1}
            />
          </Group>

          <Group title={t("hookStyleSettings.placement.title")} body={t("hookStyleSettings.placement.body")}>
            <SliderField
              label={t("hookStyleSettings.placement.x")}
              readout={t("hookStyleSettings.placement.percent", { value: num(posX * 100) })}
              value={posX}
              onChange={setPosX}
              min={0}
              max={1}
              step={0.01}
            />
            <SliderField
              label={t("hookStyleSettings.placement.y")}
              readout={t("hookStyleSettings.placement.percent", { value: num(posY * 100) })}
              value={posY}
              onChange={setPosY}
              min={0}
              max={1}
              step={0.01}
            />
            <SliderField
              label={t("hookStyleSettings.placement.duration")}
              readout={t("hookStyleSettings.placement.durationValue", { count: durationSeconds, value: num(durationSeconds, 1) })}
              hint={t("hookStyleSettings.placement.durationBody")}
              value={durationSeconds}
              onChange={setDurationSeconds}
              min={1}
              max={15}
              step={0.5}
            />
          </Group>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button onClick={() => void save()} disabled={saving || !loaded} className="h-11 gap-2 px-6">
              {saving && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
              {saving ? t("hookStyleSettings.saving") : t("hookStyleSettings.save")}
            </Button>
            <Button variant="ghost" onClick={reset} disabled={saving} className="h-11 px-4 text-[var(--color-text-secondary)]">
              {t("hookStyleSettings.reset")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Group({ title, body, first, children }: { title: string; body: string; first?: boolean; children: React.ReactNode }) {
  return (
    <section className={first ? undefined : "mt-9"}>
      <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{body}</p>
      <div className="mt-3 space-y-5 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4">
        {children}
      </div>
    </section>
  );
}

function SliderField({
  label,
  readout,
  hint,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  readout: string;
  hint?: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
}) {
  const id = useId();
  return (
    <div role="group" aria-labelledby={id} className="space-y-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <p id={id} className="text-sm font-medium text-[var(--color-text-primary)]">
          {label}
        </p>
        <span className="text-sm tabular-nums text-[var(--color-text-secondary)]">{readout}</span>
      </div>
      <Slider value={[value]} onValueChange={(v) => onChange(v[0])} min={min} max={max} step={step} className="min-h-6" />
      {hint && <p className="text-xs text-[var(--color-text-muted)]">{hint}</p>}
    </div>
  );
}

/**
 * A swatch that opens the system color picker, plus the hex code to type.
 * A full six-digit code applies as it is typed; a short one like "fc0" is
 * expanded on blur, and anything unparseable snaps back, so an invalid color
 * never reaches the renderer.
 */
function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (hex: string) => void }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  const swatch = HEX.test(value) ? value : "#000000";

  return (
    <div className="flex items-center justify-between gap-4">
      <p className="text-sm font-medium text-[var(--color-text-primary)]">{label}</p>
      <div className="flex items-center gap-2">
        <label className="relative inline-flex h-10 w-10 shrink-0 cursor-pointer overflow-hidden rounded-full border border-[var(--color-border)] focus-within:ring-2 focus-within:ring-[var(--color-border-focus)]">
          <span aria-hidden className="absolute inset-0" style={{ backgroundColor: swatch }} />
          <input
            type="color"
            value={swatch}
            onChange={(e) => onChange(e.target.value.toUpperCase())}
            aria-label={t("hookStyleSettings.color.pick", { field: label })}
            className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
          />
        </label>
        <Input
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            const hex = normalizeHex(e.target.value);
            if (hex && e.target.value.replace("#", "").trim().length === 6) onChange(hex);
          }}
          onBlur={() => {
            const hex = normalizeHex(draft);
            if (hex) onChange(hex);
            setDraft(hex ?? value);
          }}
          aria-label={t("hookStyleSettings.color.hex", { field: label })}
          spellCheck={false}
          autoComplete="off"
          maxLength={7}
          className="h-10 w-28 font-mono text-sm uppercase"
        />
      </div>
    </div>
  );
}
