import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Save, Loader2, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { listHookFonts, readFontAsBase64, type HookStyleSettings } from "@/hooks/appConfig";
import { useConfigStore } from "@/stores/configStore";

const CANVAS_W = 270;
const CANVAS_H = 480;
const VIDEO_W = 1080;

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

export function HookStyleSettingsPage() {
  const navigate = useNavigate();
  const { config, loaded, load, setHookStyle } = useConfigStore();

  const [fontName, setFontName] = useState("Arial");
  const [fontPath, setFontPath] = useState("");
  const [fonts, setFonts] = useState<{ name: string; path: string }[]>([]);
  const [fontLoading, setFontLoading] = useState(false);
  const [fontDataUrls, setFontDataUrls] = useState<Map<string, string>>(new Map());

  const [fontSize, setFontSize] = useState(0.054);
  const [fontColor, setFontColor] = useState("#FFD700");
  const [bgColor, setBgColor] = useState("#FFFFFF");
  const [cornerRadius, setCornerRadius] = useState(0);
  const [posX, setPosX] = useState(0.5);
  const [posY, setPosY] = useState(0.333);
  const [durationSeconds, setDurationSeconds] = useState(5);
  const [saving, setSaving] = useState(false);

  const canvasRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ offsetX: number; offsetY: number } | null>(null);

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
    if (fonts.length > 0) return;
    setFontLoading(true);
    listHookFonts()
      .then((result) => {
        setFonts(result);
        if (result.length === 0) return;
        const exists = result.some((f) => f.name === fontName);
        if (!exists) {
          setFontName(result[0].name);
          setFontPath(result[0].path);
        }
        // Load each font as data URL for preview
        const map = new Map<string, string>();
        const loads = result.map(async (f) => {
          try {
            const dataUrl = await readFontAsBase64(f.path);
            map.set(f.path, dataUrl);
          } catch {
            // skip
          }
        });
        Promise.allSettled(loads).then(() => setFontDataUrls(new Map(map)));
      })
      .catch((err) => {
        console.error("Failed to list hook fonts", err);
      })
      .finally(() => setFontLoading(false));
  }, [fonts.length, fontName]);

  const handleFontSelect = (name: string) => {
    setFontName(name);
    const found = fonts.find((f) => f.name === name);
    if (found) setFontPath(found.path);
  };

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const markLeft = posX * CANVAS_W;
      const markTop = posY * CANVAS_H;
      // Allow drag anywhere on canvas for convenience
      dragState.current = {
        offsetX: e.clientX - rect.left - markLeft,
        offsetY: e.clientY - rect.top - markTop,
      };
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
    },
    [posX, posY]
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
    const next: HookStyleSettings = {
      fontName,
      fontPath,
      fontSize,
      fontColor,
      bgColor,
      cornerRadius,
      positionX: posX,
      positionY: posY,
      durationSeconds,
    };
    try {
      await setHookStyle(next);
      toast.success("Hook style settings saved");
      navigate("/settings");
    } catch {
      toast.error("Failed to save hook style settings");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
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

  // Preview calculations
  const scale = CANVAS_W / VIDEO_W;
  const videoFontPx = Math.round(fontSize * VIDEO_W);
  const previewFontPx = Math.max(8, Math.round(videoFontPx * scale));
  const sampleText = "HOOK PREVIEW";
  const textWidth = Math.round(0.55 * previewFontPx * sampleText.length);
  const textHeight = Math.round(previewFontPx * 1.2);
  const padding = Math.max(6, Math.round(12 * scale * 4));
  const boxW = textWidth + padding * 2;
  const boxH = textHeight + padding * 2;
  const cx = Math.round(posX * CANVAS_W);
  const cy = Math.round(posY * CANVAS_H);
  const radiusVideo = Math.round(cornerRadius);
  const radiusCanvas = Math.max(0, Math.min(Math.round(radiusVideo * scale), boxW / 2, boxH / 2));

  const selectedFontDataUrl = fontDataUrls.get(fontPath);

  const boxStyle: React.CSSProperties = {
    position: "absolute",
    left: cx - boxW / 2,
    top: cy - boxH / 2,
    width: boxW,
    height: boxH,
    backgroundColor: bgColor,
    borderRadius: radiusCanvas,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "grab",
  };

  const textStyle: React.CSSProperties = {
    color: fontColor,
    fontSize: previewFontPx,
    fontFamily: selectedFontDataUrl
      ? `"hook-${fontName}", ${fontName}, sans-serif`
      : fontName,
    fontWeight: "bold",
    lineHeight: 1,
    userSelect: "none",
  };

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Inject @font-face for selected font so preview uses it */}
      {selectedFontDataUrl && (
        <style>{`
          @font-face {
            font-family: "hook-${fontName}";
            src: url("${selectedFontDataUrl}") format("truetype");
          }
        `}</style>
      )}

      <Button
        variant="ghost"
        onClick={() => navigate("/settings")}
        className="gap-2 text-[var(--color-text-secondary)]"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Settings
      </Button>

      <div>
        <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Hook Style</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Customize the hook text shown over the opening seconds of the clip. Drag the box on the preview to reposition it.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: controls */}
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Font</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {fontLoading ? (
                <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading fonts...
                </div>
              ) : (
                <>
                  <select
                    value={fontName}
                    onChange={(e) => handleFontSelect(e.target.value)}
                    className="w-full h-10 px-3 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)] text-sm text-[var(--color-text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--color-border-focus)]"
                  >
                    {fonts.map((f) => (
                      <option key={f.name} value={f.name}>
                        {f.name}
                      </option>
                    ))}
                  </select>

                  {/* Font preview samples */}
                  {fonts.length > 0 && (
                    <div className="space-y-1 mt-3 max-h-48 overflow-y-auto">
                      {fonts.map((f) => {
                        const dataUrl = fontDataUrls.get(f.path);
                        return (
                          <div
                            key={f.name}
                            className={`px-3 py-2 rounded-[var(--radius-sm)] cursor-pointer transition-colors ${
                              f.name === fontName
                                ? "bg-[var(--color-accent-light)] border border-[var(--color-accent)]/30"
                                : "hover:bg-[var(--color-bg-hover)]"
                            }`}
                            onClick={() => handleFontSelect(f.name)}
                          >
                            <p className="text-xs text-[var(--color-text-muted)] mb-1">{f.name}</p>
                            {dataUrl ? (
                              <div>
                                <style>{`
                                  @font-face {
                                    font-family: "hook-${f.name}";
                                    src: url("${dataUrl}") format("truetype");
                                  }
                                `}</style>
                                <p
                                  className="text-lg"
                                  style={{ fontFamily: `"hook-${f.name}", sans-serif` }}
                                >
                                  The quick brown fox jumps over the lazy dog
                                </p>
                              </div>
                            ) : (
                              <p className="text-sm text-[var(--color-text-muted)] italic">
                                {f.name}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )}

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Font Size
                  </label>
                  <span className="text-sm text-[var(--color-text-muted)]">
                    {(fontSize * 100).toFixed(1)}%
                  </span>
                </div>
                <Slider
                  value={[fontSize]}
                  onValueChange={(v) => setFontSize(v[0])}
                  min={0.025}
                  max={0.1}
                  step={0.0025}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Colors</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Font color */}
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-[var(--color-text-secondary)] w-24 shrink-0">
                  Text
                </label>
                <input
                  type="color"
                  value={fontColor}
                  onChange={(e) => setFontColor(e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer bg-transparent border-0"
                />
                <Input
                  value={fontColor}
                  onChange={(e) => setFontColor(e.target.value)}
                  className="flex-1 font-mono text-sm"
                />
              </div>

              {/* BG color */}
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-[var(--color-text-secondary)] w-24 shrink-0">
                  Background
                </label>
                <input
                  type="color"
                  value={bgColor}
                  onChange={(e) => setBgColor(e.target.value)}
                  className="w-8 h-8 rounded cursor-pointer bg-transparent border-0"
                />
                <Input
                  value={bgColor}
                  onChange={(e) => setBgColor(e.target.value)}
                  className="flex-1 font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Shape & Position</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Corner Radius
                  </label>
                  <span className="text-sm text-[var(--color-text-muted)]">{cornerRadius}px</span>
                </div>
                <Slider
                  value={[cornerRadius]}
                  onValueChange={(v) => setCornerRadius(v[0])}
                  min={0}
                  max={80}
                  step={1}
                />
                <p className="text-xs text-[var(--color-text-muted)]">
                  Output video pixels. 0 = sharp corners.
                </p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--color-text-secondary)]">
                    Hook Duration
                  </label>
                  <span className="text-sm text-[var(--color-text-muted)]">
                    {durationSeconds.toFixed(1)}s
                  </span>
                </div>
                <Slider
                  value={[durationSeconds]}
                  onValueChange={(v) => setDurationSeconds(v[0])}
                  min={1}
                  max={15}
                  step={0.5}
                />
                <p className="text-xs text-[var(--color-text-muted)]">
                  How long the hook text stays on screen from the start of the clip.
                </p>
              </div>

              <div className="text-sm text-[var(--color-text-muted)]">
                Position: {Math.round(posX * 100)}% X, {Math.round(posY * 100)}% Y
              </div>

              <Button variant="outline" size="sm" onClick={handleReset} className="w-full gap-2">
                <RotateCcw className="w-3.5 h-3.5" />
                Reset to Default
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right: preview */}
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

            {/* Hook box */}
            <div style={boxStyle} onPointerDown={onPointerDown}>
              <span style={textStyle}>{sampleText}</span>
            </div>
          </div>
          <p className="text-xs text-[var(--color-text-muted)]">
            Tip: drag anywhere on the preview to reposition
          </p>
        </div>
      </div>

      <Button onClick={handleSave} disabled={saving || !loaded} className="w-full h-12 gap-2">
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        Save hook style settings
      </Button>
    </div>
  );
}
