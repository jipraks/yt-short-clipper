import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Cpu, Loader2, RefreshCw, Zap, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { SettingRow, SettingSection } from "@/components/settings/SettingRow";
import { Input } from "@/components/ui/input";
import {
  detectGpu,
  MAX_CLIP_PADDING,
  type ClipPaddingSettings,
  type GpuDetection,
} from "@/hooks/appConfig";
import { useConfigStore } from "@/stores/configStore";

export function SettingsPage() {
  const navigate = useNavigate();
  const { config, loaded, load, setGpuAcceleration, setClipPadding } = useConfigStore();
  const [detection, setDetection] = useState<GpuDetection | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    load();
  }, [load]);

  const runDetect = async () => {
    setDetecting(true);
    try {
      const result = await detectGpu();
      setDetection(result);
    } catch (err) {
      console.error("GPU detection failed", err);
      toast.error("GPU detection failed");
    } finally {
      setDetecting(false);
    }
  };

  useEffect(() => {
    runDetect();
  }, []);

  const gpuEnabled = config.gpuAcceleration.enabled;
  const encoderAvailable = detection?.encoder.available ?? false;
  const canToggle = encoderAvailable && !detecting;

  const handleToggle = async (next: boolean) => {
    setSaving(true);
    try {
      await setGpuAcceleration(next);
      toast.success(next ? "GPU acceleration enabled" : "GPU acceleration disabled");
    } catch {
      toast.error("Failed to save setting");
    } finally {
      setSaving(false);
    }
  };

  const savePadding = async (next: ClipPaddingSettings) => {
    try {
      await setClipPadding(next);
    } catch {
      toast.error("Failed to save clip timing");
    }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Settings</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Configure performance and output options.
        </p>
      </div>

      <SettingSection
        title="GPU Acceleration"
        description="Hardware encoding is 3-5x faster than CPU. Requires a compatible GPU."
      >
        <SettingRow
          title="Detected GPU"
          description={
            detecting
              ? "Detecting..."
              : detection
                ? detection.gpu.available
                  ? `${gpuTypeLabel(detection.gpu.type)} · ${detection.gpu.name}`
                  : "No GPU detected — CPU encoding will be used"
                : "Not checked yet"
          }
        >
          <Button
            variant="outline"
            size="sm"
            onClick={runDetect}
            disabled={detecting}
            className="gap-2"
          >
            {detecting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Detect
          </Button>
        </SettingRow>

        <SettingRow
          title="Enable GPU acceleration"
          description={
            encoderAvailable
              ? `Encoder: ${detection?.encoder.name}${
                  detection?.encoder.preset ? ` · preset ${detection.encoder.preset}` : ""
                }`
              : detection?.encoder.reason ?? "Run detection to check encoder support"
          }
        >
          <div className="flex items-center gap-2">
            {saving && <Loader2 className="w-4 h-4 animate-spin text-[var(--color-text-muted)]" />}
            <Switch
              checked={gpuEnabled && encoderAvailable}
              onCheckedChange={handleToggle}
              disabled={!canToggle || saving || !loaded}
            />
          </div>
        </SettingRow>

        <SettingRow
          title="Active encoder"
          description="What will be used when processing video."
        >
          <span className="inline-flex items-center gap-2 text-sm font-medium">
            {gpuEnabled && encoderAvailable ? (
              <>
                <Zap className="w-4 h-4 text-[var(--color-success)]" />
                <span className="text-[var(--color-success)]">
                  {detection?.encoder.name}
                </span>
              </>
            ) : (
              <>
                <Cpu className="w-4 h-4 text-[var(--color-text-muted)]" />
                <span className="text-[var(--color-text-secondary)]">libx264 (CPU)</span>
              </>
            )}
          </span>
        </SettingRow>
      </SettingSection>

      <SettingSection
        title="Clip Timing"
        description="Extra footage kept around each clip so sentences aren't cut off."
      >
        <SettingRow
          title="Lead-in"
          description="Seconds kept before the start the AI picked."
        >
          <PaddingInput
            value={config.clipPadding.leadIn}
            disabled={!loaded}
            onCommit={(leadIn) => savePadding({ ...config.clipPadding, leadIn })}
          />
        </SettingRow>

        <SettingRow
          title="Tail-out"
          description="Seconds kept after the end the AI picked. Usually the one that matters — subtitle cues tend to end while the speaker is still talking."
        >
          <PaddingInput
            value={config.clipPadding.tailOut}
            disabled={!loaded}
            onCommit={(tailOut) => savePadding({ ...config.clipPadding, tailOut })}
          />
        </SettingRow>

        <SettingRow
          title="Net effect"
          description="Applied to the cut itself — captions shift with it, so they stay in sync."
        >
          <span className="text-sm font-medium text-[var(--color-text-secondary)]">
            {config.clipPadding.leadIn + config.clipPadding.tailOut === 0
              ? "Exact range, no padding"
              : `+${(config.clipPadding.leadIn + config.clipPadding.tailOut).toFixed(1)}s per clip`}
          </span>
        </SettingRow>
      </SettingSection>

      <SettingSection
        title="Output"
        description="Branding and overlays applied to every clip."
      >
        <SettingRow
          title="Watermark"
          description={
            config.watermark.enabled
              ? "Enabled — overlay a logo on each clip"
              : "Add a logo overlay to each clip"
          }
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/settings/watermark")}
            className="gap-2"
          >
            Configure
            <ChevronRight className="w-4 h-4" />
          </Button>
        </SettingRow>

        <SettingRow
          title="Credit Text"
          description={
            config.creditWatermark.enabled
              ? "Enabled — credit overlay on each clip"
              : "Add source channel credit overlay"
          }
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/settings/credit")}
            className="gap-2"
          >
            Configure
            <ChevronRight className="w-4 h-4" />
          </Button>
        </SettingRow>

        <SettingRow
          title="Hook Style"
          description={
            "Font, colors, and shape of the opening hook scene"
          }
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/settings/hook-style")}
            className="gap-2"
          >
            Configure
            <ChevronRight className="w-4 h-4" />
          </Button>
        </SettingRow>
      </SettingSection>

      <SettingSection
        title="Integrations"
        description="Connect external services for publishing your clips."
      >
        <SettingRow
          title="Repliz"
          description={
            config.repliz.accessKey && config.repliz.secretKey
              ? "Connected — upload clips to multiple platforms"
              : "Upload clips to YouTube, TikTok, Instagram, and more"
          }
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/settings/repliz")}
            className="gap-2"
          >
            Configure
            <ChevronRight className="w-4 h-4" />
          </Button>
        </SettingRow>
      </SettingSection>

      <SettingSection
        title="About"
        description="Application information and credits."
      >
        <SettingRow
          title="Open Source Credits"
          description="Libraries and tools used in this application"
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/settings/credits")}
            className="gap-2"
          >
            View
            <ChevronRight className="w-4 h-4" />
          </Button>
        </SettingRow>
      </SettingSection>
    </div>
  );
}

interface PaddingInputProps {
  value: number;
  disabled: boolean;
  onCommit: (seconds: number) => void;
}

/**
 * Seconds input that commits on blur or Enter rather than per keystroke.
 *
 * It keeps its own draft string so a half-typed value ("1." on the way to
 * "1.5") isn't parsed and written back mid-edit, and re-syncs whenever the
 * stored value changes underneath it — which it does once on mount, when the
 * real config replaces the defaults.
 */
function PaddingInput({ value, disabled, onCommit }: PaddingInputProps) {
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    setDraft(String(value));
  }, [value]);

  const commit = () => {
    const parsed = Number(draft.replace(",", "."));
    // Anything unparseable or out of range snaps back to the stored value
    // rather than silently writing a nonsense padding.
    if (!Number.isFinite(parsed) || parsed < 0) {
      setDraft(String(value));
      return;
    }
    const clamped = Math.min(Math.round(parsed * 10) / 10, MAX_CLIP_PADDING);
    setDraft(String(clamped));
    if (clamped !== value) onCommit(clamped);
  };

  return (
    <div className="flex items-center gap-2">
      <Input
        type="number"
        inputMode="decimal"
        min={0}
        max={MAX_CLIP_PADDING}
        step={0.5}
        value={draft}
        disabled={disabled}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
        }}
        className="w-24 text-right"
      />
      <span className="text-sm text-[var(--color-text-muted)]">sec</span>
    </div>
  );
}

function gpuTypeLabel(type: string | null): string {
  switch (type) {
    case "nvidia":
      return "NVIDIA";
    case "amd":
      return "AMD";
    case "intel":
      return "Intel";
    case "apple":
      return "Apple";
    default:
      return "GPU";
  }
}
