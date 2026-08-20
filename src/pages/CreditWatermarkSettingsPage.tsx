import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { useConfigStore } from "@/stores/configStore";
import type { CreditWatermarkSettings } from "@/hooks/appConfig";

const CANVAS_W = 270;
const CANVAS_H = 480;

export function CreditWatermarkSettingsPage() {
  const navigate = useNavigate();
  const { config, loaded, load, setCreditWatermark } = useConfigStore();

  const [enabled, setEnabled] = useState(false);
  const [text, setText] = useState("Source: {channel}");
  const [color, setColor] = useState("#FFFFFF");
  const [fontSize, setFontSize] = useState(24);
  const [opacity, setOpacity] = useState(0.7);
  const [posX, setPosX] = useState(0.03);
  const [posY, setPosY] = useState(0.92);
  const [saving, setSaving] = useState(false);

  const canvasRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ offsetX: number; offsetY: number } | null>(null);

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

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (!enabled) return;
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
    [enabled, posX, posY]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragState.current) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      let x = e.clientX - rect.left - dragState.current.offsetX;
      let y = e.clientY - rect.top - dragState.current.offsetY;
      x = Math.max(0, Math.min(x, CANVAS_W));
      y = Math.max(0, Math.min(y, CANVAS_H));
      setPosX(x / CANVAS_W);
      setPosY(y / CANVAS_H);
    },
    []
  );

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    dragState.current = null;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    const next: CreditWatermarkSettings = {
      enabled,
      text: text.trim() || "Source: {channel}",
      color,
      fontSize,
      opacity,
      positionX: posX,
      positionY: posY,
    };
    try {
      await setCreditWatermark(next);
      toast.success("Credit watermark settings saved");
      navigate("/settings");
    } catch {
      toast.error("Failed to save credit watermark settings");
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
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Credit Watermark</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Overlay a text credit for the source channel. Use {"{channel}"} to auto-insert the channel name.
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
              <CardTitle>Text</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder='e.g. "Source: {channel}"'
              />
              <p className="text-xs text-[var(--color-text-muted)]">
                {"{channel}"} will be replaced with the YouTube channel name.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Appearance</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Color */}
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                  Color
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="color"
                    value={color}
                    onChange={(e) => setColor(e.target.value)}
                    className="w-10 h-10 rounded-[var(--radius-sm)] border border-[var(--color-border)] cursor-pointer bg-transparent"
                  />
                  <Input
                    value={color}
                    onChange={(e) => setColor(e.target.value)}
                    className="flex-1 font-mono text-sm"
                    placeholder="#FFFFFF"
                  />
                </div>
              </div>

              {/* Font Size */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Font Size
                  </label>
                  <span className="text-sm text-[var(--color-text-muted)]">
                    {fontSize}px
                  </span>
                </div>
                <Slider
                  value={[fontSize]}
                  onValueChange={(v) => setFontSize(v[0])}
                  min={12}
                  max={72}
                  step={1}
                />
              </div>

              {/* Opacity */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Transparency
                  </label>
                  <span className="text-sm text-[var(--color-text-muted)]">
                    {Math.round(opacity * 100)}%
                  </span>
                </div>
                <Slider
                  value={[opacity]}
                  onValueChange={(v) => setOpacity(v[0])}
                  min={0.1}
                  max={1}
                  step={0.05}
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

            {/* Credit text */}
            {enabled && (
              <div
                onPointerDown={onPointerDown}
                className="absolute cursor-grab active:cursor-grabbing whitespace-nowrap select-none"
                style={{
                  left: `${posX * CANVAS_W}px`,
                  top: `${posY * CANVAS_H}px`,
                  color,
                  fontSize: `${fontSize}px`,
                  opacity,
                  textShadow: "0 0 4px rgba(0,0,0,0.8)",
                }}
              >
                {text}
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
        Save credit watermark settings
      </Button>
    </div>
  );
}
