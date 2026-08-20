import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Upload, Loader2, Save, ImageOff } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { useConfigStore } from "@/stores/configStore";
import { saveWatermark, readWatermark, type WatermarkSettings } from "@/hooks/appConfig";

const CANVAS_W = 270;
const CANVAS_H = 480;

export function WatermarkSettingsPage() {
  const navigate = useNavigate();
  const { config, loaded, load, setWatermark } = useConfigStore();

  const [enabled, setEnabled] = useState(false);
  const [imagePath, setImagePath] = useState("");
  const [posX, setPosX] = useState(0.85);
  const [posY, setPosY] = useState(0.05);
  const [opacity, setOpacity] = useState(0.8);
  const [scale, setScale] = useState(0.15);
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ offsetX: number; offsetY: number } | null>(null);

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
    if (w.imagePath) {
      readWatermark(w.imagePath)
        .then(setDataUrl)
        .catch(() => setDataUrl(null));
    }
  }, [loaded, config.watermark]);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const buf = new Uint8Array(await file.arrayBuffer());
      const saved = await saveWatermark(file.name, buf);
      setImagePath(saved.path);
      setDataUrl(saved.dataUrl);
      toast.success("Watermark image loaded");
    } catch (err) {
      console.error("Failed to upload watermark", err);
      toast.error("Failed to load watermark image");
    }
    e.target.value = "";
  };

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!enabled || !dataUrl) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const markLeft = posX * CANVAS_W;
      const markTop = posY * CANVAS_H;
      dragState.current = {
        offsetX: e.clientX - rect.left - markLeft,
        offsetY: e.clientY - rect.top - markTop,
      };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [enabled, dataUrl, posX, posY]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragState.current) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const markW = scale * CANVAS_W;
      const markH = markW; // clamp roughly within frame
      let x = e.clientX - rect.left - dragState.current.offsetX;
      let y = e.clientY - rect.top - dragState.current.offsetY;
      x = Math.max(0, Math.min(x, CANVAS_W - markW));
      y = Math.max(0, Math.min(y, CANVAS_H - markH));
      setPosX(x / CANVAS_W);
      setPosY(y / CANVAS_H);
    },
    [scale]
  );

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    dragState.current = null;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  }, []);

  const handleSave = async () => {
    if (enabled && !imagePath) {
      toast.error("Please select a watermark image");
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
      toast.success("Watermark settings saved");
      navigate("/settings");
    } catch {
      toast.error("Failed to save watermark settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5 max-w-3xl">
      <Button
        variant="ghost"
        onClick={() => navigate("/settings")}
        className="gap-2 text-[var(--color-text-secondary)]"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Settings
      </Button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Watermark</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Overlay a logo on every clip. Drag it on the preview to position it.
          </p>
        </div>
        <Switch checked={enabled} onCheckedChange={setEnabled} />
      </div>

      <div
        className={`grid grid-cols-1 md:grid-cols-2 gap-5 transition-opacity ${
          enabled ? "opacity-100" : "opacity-50 pointer-events-none"
        }`}
      >
        {/* Left: controls */}
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Image</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <input
                ref={fileRef}
                type="file"
                accept=".png,.jpg,.jpeg"
                onChange={handleFile}
                className="hidden"
              />
              <Button
                variant="outline"
                onClick={() => fileRef.current?.click()}
                className="w-full gap-2 h-11"
              >
                <Upload className="w-4 h-4" />
                {imagePath ? "Replace image" : "Upload PNG / JPG"}
              </Button>
              {imagePath && (
                <p className="text-xs text-[var(--color-text-muted)] truncate">
                  {imagePath.split(/[\\/]/).pop()}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Opacity
                  </label>
                  <span className="text-sm text-[var(--color-text-muted)]">
                    {Math.round(opacity * 100)}%
                  </span>
                </div>
                <Slider
                  value={[opacity]}
                  onValueChange={(v) => setOpacity(v[0])}
                  min={0}
                  max={1}
                  step={0.05}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Size
                  </label>
                  <span className="text-sm text-[var(--color-text-muted)]">
                    {Math.round(scale * 100)}%
                  </span>
                </div>
                <Slider
                  value={[scale]}
                  onValueChange={(v) => setScale(v[0])}
                  min={0.05}
                  max={0.5}
                  step={0.01}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right: 9:16 preview */}
        <div className="flex flex-col items-center gap-2">
          <p className="text-sm font-medium text-[var(--color-text-secondary)] self-start">
            Preview (9:16)
          </p>
          <div
            ref={canvasRef}
            className="relative rounded-[var(--radius)] overflow-hidden border border-[var(--color-border)] bg-[#15151a] select-none"
            style={{ width: CANVAS_W, height: CANVAS_H }}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
          >
            {/* center hint */}
            <div className="absolute inset-0 flex items-center justify-center text-[var(--color-text-muted)] text-xs pointer-events-none">
              9:16 Video
            </div>

            {dataUrl ? (
              <img
                src={dataUrl}
                alt="watermark"
                draggable={false}
                onPointerDown={onPointerDown}
                className="absolute cursor-grab active:cursor-grabbing"
                style={{
                  left: `${posX * CANVAS_W}px`,
                  top: `${posY * CANVAS_H}px`,
                  width: `${scale * CANVAS_W}px`,
                  opacity,
                }}
              />
            ) : (
              <div className="absolute bottom-3 left-0 right-0 flex flex-col items-center gap-1 text-[var(--color-text-muted)]">
                <ImageOff className="w-6 h-6 opacity-50" />
                <span className="text-xs">No watermark image</span>
              </div>
            )}
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">
            Position: {Math.round(posX * 100)}%, {Math.round(posY * 100)}%
          </p>
        </div>
      </div>

      <Button onClick={handleSave} disabled={saving || !loaded} className="w-full h-12 gap-2">
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        Save watermark settings
      </Button>
    </div>
  );
}
