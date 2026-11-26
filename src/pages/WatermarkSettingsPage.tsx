import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { ArrowLeft, ImageOff, Loader2, Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useConfigStore } from "@/stores/configStore";
import { saveWatermark, readWatermark, type WatermarkSettings } from "@/hooks/appConfig";
import { cn } from "@/lib/utils";

const FRAME_W = 270;
const FRAME_H = 480;
// Clips come out at 1080x1920, and ffmpeg scales the logo from its own pixel
// size (scale=iw*scale), so the preview needs both to show the real size.
const OUT_W = 1080;
const OUT_H = 1920;
const MAX_BYTES = 5 * 1024 * 1024;
const MARGIN_X = 0.04;
const MARGIN_Y = (MARGIN_X * OUT_W) / OUT_H;
const IMAGE_EXT = /\.(png|jpe?g)$/i;

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

function dataUrlToBytes(dataUrl: string): Uint8Array {
  const binary = atob(dataUrl.slice(dataUrl.indexOf(",") + 1));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

export function WatermarkSettingsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { config, loaded, load, setWatermark } = useConfigStore();
  const switchId = useId();

  const [enabled, setEnabled] = useState(false);
  const [imagePath, setImagePath] = useState("");
  const [posX, setPosX] = useState(0.85);
  const [posY, setPosY] = useState(0.05);
  const [opacity, setOpacity] = useState(0.8);
  const [scale, setScale] = useState(0.15);
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [saving, setSaving] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ dx: number; dy: number } | null>(null);
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!loaded) return;
    const w = config.watermark;
    setEnabled(w.enabled);
    setImagePath(w.imagePath);
    setPosX(w.positionX);
    setPosY(w.positionY);
    setOpacity(w.opacity);
    setScale(w.scale);
    setImageError(null);
    if (w.imagePath) {
      readWatermark(w.imagePath)
        .then(setDataUrl)
        .catch(() => {
          setDataUrl(null);
          setImageError(t("logoSettings.image.missing"));
        });
    }
  }, [loaded, config.watermark, t]);

  // Logo size as a fraction of the frame. Until the image loads, assume a square.
  const logoW = natural ? (natural.w * scale) / OUT_W : scale;
  const logoH = natural ? (natural.h * scale) / OUT_H : (logoW * FRAME_W) / FRAME_H;

  const presetPosition = (p: Preset) => ({
    x: clamp01(p.h === "left" ? MARGIN_X + logoW / 2 : p.h === "right" ? 1 - MARGIN_X - logoW / 2 : 0.5),
    y: clamp01(p.v === "top" ? MARGIN_Y + logoH / 2 : 1 - MARGIN_Y - logoH / 2),
  });

  const storeBytes = async (name: string, bytes: Uint8Array) => {
    if (bytes.length > MAX_BYTES) {
      setImageError(t("logoSettings.errors.tooBig", { size: (bytes.length / 1024 / 1024).toFixed(1) }));
      return;
    }
    const saved = await saveWatermark(name, bytes);
    setImagePath(saved.path);
    setNatural(null);
    setDataUrl(saved.dataUrl);
    setImageError(null);
    toast.success(t("logoSettings.loaded"));
  };

  const addFromFile = async (file: File) => {
    if (!IMAGE_EXT.test(file.name)) {
      setImageError(t("logoSettings.errors.wrongType"));
      return;
    }
    if (file.size > MAX_BYTES) {
      setImageError(t("logoSettings.errors.tooBig", { size: (file.size / 1024 / 1024).toFixed(1) }));
      return;
    }
    setUploading(true);
    try {
      await storeBytes(file.name, new Uint8Array(await file.arrayBuffer()));
    } catch (err) {
      console.error("Failed to upload watermark", err);
      setImageError(t("logoSettings.errors.uploadFailed", { reason: String(err) }));
    } finally {
      setUploading(false);
    }
  };

  const addFromPath = async (path: string) => {
    const name = path.split(/[\\/]/).pop() ?? path;
    if (!IMAGE_EXT.test(name)) {
      setImageError(t("logoSettings.errors.wrongType"));
      return;
    }
    setUploading(true);
    try {
      await storeBytes(name, dataUrlToBytes(await readWatermark(path)));
    } catch (err) {
      console.error("Failed to load dropped watermark", err);
      setImageError(t("logoSettings.errors.uploadFailed", { reason: String(err) }));
    } finally {
      setUploading(false);
    }
  };

  const addFromPathRef = useRef(addFromPath);
  addFromPathRef.current = addFromPath;

  // Tauri takes over file drops in the window, so HTML drop events never see
  // the file. Its own event hands us the path instead.
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let cancelled = false;
    try {
      getCurrentWebview()
        .onDragDropEvent((event) => {
          const p = event.payload;
          if (p.type === "enter") {
            if (enabledRef.current) setDragActive(true);
          } else if (p.type === "leave") {
            setDragActive(false);
          } else if (p.type === "drop") {
            setDragActive(false);
            if (!p.paths.length) return;
            if (!enabledRef.current) {
              toast.error(t("logoSettings.errors.turnOnFirst"));
              return;
            }
            void addFromPathRef.current(p.paths[0]);
          }
        })
        .then((fn) => {
          if (cancelled) fn();
          else unlisten = fn;
        })
        .catch(() => {});
    } catch {
      // Not running inside Tauri.
    }
    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, [t]);

  const handleInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file) await addFromFile(file);
  };

  const removeImage = () => {
    setImagePath("");
    setDataUrl(null);
    setNatural(null);
    setImageError(null);
  };

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
      const halfW = Math.min(logoW / 2, 0.5);
      const halfH = Math.min(logoH / 2, 0.5);
      setPosX(round3(Math.min(1 - halfW, Math.max(halfW, x))));
      setPosY(round3(Math.min(1 - halfH, Math.max(halfH, y))));
    },
    [logoW, logoH],
  );

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    dragState.current = null;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  }, []);

  const handleSave = async () => {
    if (enabled && !imagePath) {
      toast.error(t("logoSettings.errors.needImage"));
      return;
    }
    setSaving(true);
    const next: WatermarkSettings = {
      enabled,
      imagePath,
      positionX: posX,
      positionY: posY,
      opacity,
      scale,
    };
    try {
      await setWatermark(next);
      toast.success(t("logoSettings.saved"));
      navigate("/settings");
    } catch (err) {
      toast.error(t("logoSettings.saveFailed", { reason: String(err) }));
    } finally {
      setSaving(false);
    }
  };

  const fileName = imagePath.split(/[\\/]/).pop();
  const sizeLabel = natural
    ? t("logoSettings.look.sizeOfFrame", { pct: Math.round(logoW * 100) })
    : t("logoSettings.look.sizeRaw", { pct: Math.round(scale * 100) });

  return (
    <div className="mx-auto max-w-4xl py-4">
      <button
        type="button"
        onClick={() => navigate("/settings")}
        className="-ml-2 inline-flex min-h-10 items-center gap-1.5 rounded-full px-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
      >
        <ArrowLeft aria-hidden className="h-4 w-4" />
        {t("logoSettings.back")}
      </button>

      <h1 className="mt-4 text-2xl font-bold text-[var(--color-text-primary)]">{t("logoSettings.title")}</h1>
      <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{t("logoSettings.subtitle")}</p>

      {!loaded ? (
        <div className="mt-9 flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          {t("logoSettings.loading")}
        </div>
      ) : (
        <div className="mt-8 grid gap-8 md:grid-cols-[270px_minmax(0,1fr)] md:gap-10">
          {/* Preview */}
          <div className="md:sticky md:top-4 md:self-start">
            <p className="text-sm font-medium text-[var(--color-text-primary)]">{t("logoSettings.preview.label")}</p>
            <div
              ref={frameRef}
              role="img"
              aria-label={t("logoSettings.preview.aria")}
              className="relative mt-3 mx-auto overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-gradient-to-b from-[var(--color-bg-card)] to-black select-none touch-none"
              style={{ width: FRAME_W, height: FRAME_H }}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
            >
              <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-xs text-[var(--color-text-muted)]">
                {t("logoSettings.preview.frame")}
              </span>
              {dataUrl ? (
                <img
                  src={dataUrl}
                  alt=""
                  draggable={false}
                  onLoad={(e) => setNatural({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
                  onPointerDown={onPointerDown}
                  className={cn("absolute max-w-none", enabled ? "cursor-grab active:cursor-grabbing" : "grayscale")}
                  style={{
                    left: (posX - logoW / 2) * FRAME_W,
                    top: (posY - logoH / 2) * FRAME_H,
                    width: logoW * FRAME_W,
                    opacity: enabled ? opacity : opacity * 0.35,
                  }}
                />
              ) : (
                <div className="pointer-events-none absolute inset-x-0 bottom-4 flex flex-col items-center gap-1 text-[var(--color-text-muted)]">
                  <ImageOff aria-hidden className="h-5 w-5" />
                  <span className="text-xs">{t("logoSettings.preview.empty")}</span>
                </div>
              )}
            </div>
            <p className="mt-2 text-center text-xs text-[var(--color-text-muted)]">
              {enabled ? t("logoSettings.preview.hint") : t("logoSettings.preview.off")}
            </p>
          </div>

          {/* Controls */}
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg-primary)] p-4">
              <div className="min-w-0">
                <label htmlFor={switchId} className="text-sm font-medium text-[var(--color-text-primary)] cursor-pointer">
                  {t("logoSettings.enable.title")}
                </label>
                <p className="mt-0.5 text-xs text-[var(--color-text-muted)] leading-relaxed">{t("logoSettings.enable.body")}</p>
              </div>
              <Switch id={switchId} checked={enabled} onCheckedChange={setEnabled} />
            </div>

            <fieldset disabled={!enabled} className={cn("min-w-0 transition-opacity", !enabled && "opacity-50")}>
              <Section title={t("logoSettings.image.title")} body={t("logoSettings.image.body")}>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                  onChange={handleInput}
                  className="hidden"
                />
                {imagePath && !dragActive ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)]">
                      {dataUrl ? (
                        <img src={dataUrl} alt={t("logoSettings.preview.logoAlt")} className="max-h-full max-w-full object-contain" />
                      ) : (
                        <ImageOff aria-hidden className="h-5 w-5 text-[var(--color-text-muted)]" />
                      )}
                    </div>
                    <p className="min-w-0 flex-1 truncate text-sm text-[var(--color-text-primary)]" title={fileName}>
                      {uploading ? t("logoSettings.image.uploading") : fileName}
                    </p>
                    <div className="flex gap-2">
                      <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={uploading}>
                        {uploading && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
                        {t("logoSettings.image.replace")}
                      </Button>
                      <Button variant="ghost" onClick={removeImage} disabled={uploading}>
                        {t("logoSettings.image.remove")}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => fileRef.current?.click()}
                    disabled={uploading}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      const file = e.dataTransfer.files?.[0];
                      if (file) void addFromFile(file);
                    }}
                    className={cn(
                      "flex min-h-28 w-full flex-col items-center justify-center gap-2 rounded-[var(--radius)] border border-dashed px-4 py-6 text-sm transition-colors cursor-pointer disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]",
                      dragActive
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-light)] text-[var(--color-text-primary)]"
                        : "border-[var(--color-border)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]",
                    )}
                  >
                    {uploading ? (
                      <>
                        <Loader2 aria-hidden className="h-5 w-5 animate-spin" />
                        {t("logoSettings.image.uploading")}
                      </>
                    ) : dragActive ? (
                      <>
                        <Upload aria-hidden className="h-5 w-5 text-[var(--color-accent)]" />
                        {t("logoSettings.image.dropActive")}
                      </>
                    ) : (
                      <>
                        <Upload aria-hidden className="h-5 w-5 text-[var(--color-text-muted)]" />
                        <span>
                          {t("logoSettings.image.drop")}{" "}
                          <span className="font-medium text-[var(--color-accent)]">{t("logoSettings.image.pick")}</span>
                        </span>
                      </>
                    )}
                  </button>
                )}
                {imageError && (
                  <p role="alert" className="mt-3 text-xs text-[var(--color-error)]">
                    {imageError}
                  </p>
                )}
              </Section>

              <Section title={t("logoSettings.position.title")} body={t("logoSettings.position.body")}>
                <PositionPresets
                  label={t("logoSettings.position.presetsAria")}
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
                  name={(p) => t(`logoSettings.position.presets.${p.id}`)}
                />
                <div className="mt-5 space-y-5">
                  <SliderRow
                    label={t("logoSettings.position.x")}
                    value={t("logoSettings.position.value", { pct: Math.round(posX * 100) })}
                    disabled={!enabled}
                    slider={{ value: [posX], onValueChange: (v) => setPosX(v[0]), min: 0, max: 1, step: 0.01 }}
                  />
                  <SliderRow
                    label={t("logoSettings.position.y")}
                    value={t("logoSettings.position.value", { pct: Math.round(posY * 100) })}
                    disabled={!enabled}
                    slider={{ value: [posY], onValueChange: (v) => setPosY(v[0]), min: 0, max: 1, step: 0.01 }}
                  />
                </div>
              </Section>

              <Section title={t("logoSettings.look.title")}>
                <div className="space-y-5">
                  <SliderRow
                    label={t("logoSettings.look.opacity")}
                    value={`${Math.round(opacity * 100)}%`}
                    disabled={!enabled}
                    slider={{ value: [opacity], onValueChange: (v) => setOpacity(v[0]), min: 0, max: 1, step: 0.05 }}
                  />
                  <SliderRow
                    label={t("logoSettings.look.size")}
                    value={sizeLabel}
                    disabled={!enabled}
                    slider={{ value: [scale], onValueChange: (v) => setScale(v[0]), min: 0.05, max: 0.5, step: 0.01 }}
                  />
                </div>
              </Section>
            </fieldset>

            <div className="mt-8 flex justify-end">
              <Button onClick={handleSave} disabled={saving || uploading} className="min-w-32">
                {saving && <Loader2 aria-hidden className="h-4 w-4 animate-spin" />}
                {saving ? t("logoSettings.saving") : t("logoSettings.save")}
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
