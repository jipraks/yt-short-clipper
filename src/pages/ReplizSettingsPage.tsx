import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Save,
  Loader2,
  ExternalLink,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  PlugZap,
  Youtube,
  Music2,
  Instagram,
  Facebook,
  Hash,
} from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useConfigStore } from "@/stores/configStore";
import type { ReplizSettings } from "@/hooks/appConfig";
import { replizListAccounts, type ReplizAccount } from "@/hooks/repliz";

function platformIcon(type: string) {
  switch (type) {
    case "youtube":
      return <Youtube className="w-4 h-4 text-red-500" />;
    case "tiktok":
      return <Music2 className="w-4 h-4" />;
    case "instagram":
      return <Instagram className="w-4 h-4 text-pink-500" />;
    case "facebook":
      return <Facebook className="w-4 h-4 text-blue-500" />;
    case "threads":
      return <Hash className="w-4 h-4" />;
    default:
      return <Hash className="w-4 h-4 text-[var(--color-text-muted)]" />;
  }
}

export function ReplizSettingsPage() {
  const navigate = useNavigate();
  const { config, loaded, load, setRepliz } = useConfigStore();

  const [accessKey, setAccessKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [saving, setSaving] = useState(false);

  // Validation state
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<
    { ok: boolean; message: string; accounts: ReplizAccount[] } | null
  >(null);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!loaded) return;
    setAccessKey(config.repliz.accessKey);
    setSecretKey(config.repliz.secretKey);
  }, [loaded, config.repliz]);

  const isConfigured = accessKey.trim() !== "" && secretKey.trim() !== "";

  const handleValidate = async () => {
    if (!isConfigured) {
      toast.error("Enter both Access Key and Secret Key first");
      return;
    }
    setValidating(true);
    setValidation(null);
    try {
      const accounts = await replizListAccounts(accessKey.trim(), secretKey.trim());
      setValidation({
        ok: true,
        message: `Connected — ${accounts.length} account(s) found`,
        accounts,
      });
      toast.success("Repliz keys are valid");
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setValidation({ ok: false, message: msg, accounts: [] });
      toast.error("Validation failed");
    } finally {
      setValidating(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    const next: ReplizSettings = {
      accessKey: accessKey.trim(),
      secretKey: secretKey.trim(),
    };
    try {
      await setRepliz(next);
      toast.success("Repliz settings saved");
      navigate("/settings");
    } catch {
      toast.error("Failed to save Repliz settings");
    } finally {
      setSaving(false);
    }
  };

  const openSignup = () => {
    openUrl("https://s.id/ytrepliz").catch(console.error);
  };

  return (
    <div className="space-y-5 max-w-2xl">
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
          <h1 className="text-xl font-bold text-[var(--color-text-primary)]">Repliz Integration</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Upload clips to multiple platforms at once (YouTube, TikTok, Instagram, Facebook).
          </p>
        </div>
        {isConfigured && (
          <span className="flex items-center gap-1.5 text-sm text-[var(--color-success)] shrink-0">
            <CheckCircle2 className="w-4 h-4" />
            Configured
          </span>
        )}
      </div>

      {/* Why Repliz */}
      <Card className="bg-[var(--color-success-bg)]/30 border-[var(--color-success)]/20">
        <CardContent className="pt-5 space-y-2">
          <p className="text-sm font-semibold text-[var(--color-text-primary)]">Why use Repliz?</p>
          <ul className="text-sm text-[var(--color-text-secondary)] space-y-1 list-disc list-inside">
            <li>Upload to all platforms at once</li>
            <li>Official API integration — safe from bans</li>
            <li>Schedule posts in advance across platforms</li>
            <li>No complex Google Console or TikTok Developer setup</li>
          </ul>
          <Button variant="outline" size="sm" onClick={openSignup} className="gap-2 mt-2">
            <ExternalLink className="w-3.5 h-3.5" />
            Sign up for Repliz
          </Button>
        </CardContent>
      </Card>

      {/* API Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>API Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)]">
              Access Key
            </label>
            <Input
              value={accessKey}
              onChange={(e) => {
                setAccessKey(e.target.value);
                setValidation(null);
              }}
              placeholder="Enter your Repliz Access Key"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-[var(--color-text-secondary)]">
              Secret Key
            </label>
            <div className="relative">
              <Input
                type={showSecret ? "text" : "password"}
                value={secretKey}
                onChange={(e) => {
                  setSecretKey(e.target.value);
                  setValidation(null);
                }}
                placeholder="Enter your Repliz Secret Key"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowSecret((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              >
                {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-xs text-[var(--color-text-muted)]">
              Your Secret Key is stored locally and never shared.
            </p>
          </div>

          {/* Validate / Load accounts */}
          <Button
            variant="outline"
            onClick={handleValidate}
            disabled={validating || !isConfigured}
            className="w-full gap-2"
          >
            {validating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <PlugZap className="w-4 h-4" />
            )}
            {validating ? "Validating..." : "Validate & Load Accounts"}
          </Button>

          {/* Validation result */}
          {validation && (
            <div
              className={`rounded-[var(--radius-sm)] border p-3 space-y-2 ${
                validation.ok
                  ? "border-[var(--color-success)]/30 bg-[var(--color-success-bg)]/20"
                  : "border-[var(--color-error)]/30 bg-[var(--color-error-bg)]/20"
              }`}
            >
              <div className="flex items-center gap-2 text-sm">
                {validation.ok ? (
                  <CheckCircle2 className="w-4 h-4 text-[var(--color-success)] shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-[var(--color-error)] shrink-0" />
                )}
                <span
                  className={
                    validation.ok
                      ? "text-[var(--color-success)]"
                      : "text-[var(--color-error)]"
                  }
                >
                  {validation.message}
                </span>
              </div>

              {validation.ok && validation.accounts.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  {validation.accounts.map((acc) => (
                    <div
                      key={acc.id}
                      className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]"
                    >
                      {platformIcon(acc.type)}
                      <span className="font-medium text-[var(--color-text-primary)]">
                        {acc.name}
                      </span>
                      {acc.username && (
                        <span className="text-[var(--color-text-muted)]">@{acc.username}</span>
                      )}
                      {acc.is_connected ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-success)] ml-auto" />
                      ) : (
                        <span className="text-xs text-[var(--color-text-muted)] ml-auto">
                          not connected
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {validation.ok && validation.accounts.length === 0 && (
                <p className="text-xs text-[var(--color-text-muted)]">
                  Keys are valid, but no accounts are connected yet. Connect your social media
                  accounts in the Repliz dashboard.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Button onClick={handleSave} disabled={saving || !loaded} className="w-full h-12 gap-2">
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        Save Repliz settings
      </Button>
    </div>
  );
}
