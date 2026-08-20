import { ExternalLink, X, Download } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { LatestVersionResponse } from "@/hooks/versionCheck";
import { APP_VERSION } from "@/config/version";

interface UpdateDialogProps {
  update: LatestVersionResponse;
  onClose: () => void;
}

export function UpdateDialog({ update, onClose }: UpdateDialogProps) {
  const handleDownload = () => {
    openUrl(update.download_url).catch(console.error);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Download className="w-5 h-5 text-[var(--color-accent)]" />
              Update Available
            </CardTitle>
            <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-[var(--color-text-secondary)]">
            A new version of YT Short Clipper is available.
          </p>

          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--color-text-muted)]">Current version</span>
              <span className="font-medium text-[var(--color-text-primary)]">{APP_VERSION}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-muted)]">Latest version</span>
              <span className="font-medium text-[var(--color-accent)]">{update.version}</span>
            </div>
          </div>

          {update.changelog && (
            <div className="p-3 rounded-[var(--radius-sm)] bg-[var(--color-bg-secondary)]">
              <p className="text-xs font-medium text-[var(--color-text-secondary)] mb-1">
                What&apos;s new
              </p>
              <p className="text-xs text-[var(--color-text-muted)] whitespace-pre-line">
                {update.changelog}
              </p>
            </div>
          )}

          <div className="flex gap-2 pt-1">
            <Button variant="outline" onClick={onClose} className="flex-1">
              Later
            </Button>
            <Button onClick={handleDownload} className="flex-1 gap-2">
              <ExternalLink className="w-4 h-4" />
              Download Update
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
