import { X, Megaphone, ExternalLink } from "lucide-react";
import { useState } from "react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { NotificationResponse } from "@/hooks/notificationCheck";

interface NotificationDialogProps {
  notification: NotificationResponse;
  onClose: () => void;
  title?: string;
}

const DISMISS_PREFIX = "ytclip-notif-dismissed:";

function dismissalKey(notification: NotificationResponse): string {
  const base = notification.message || notification.image || "announcement";
  return DISMISS_PREFIX + base.slice(0, 120);
}

export function notificationDismissed(notification: NotificationResponse): boolean {
  try {
    return localStorage.getItem(dismissalKey(notification)) === "1";
  } catch {
    return false;
  }
}

export function NotificationDialog({ notification, onClose, title = "Announcement" }: NotificationDialogProps) {
  const [dontShowAgain, setDontShowAgain] = useState(false);

  const handleClose = () => {
    if (dontShowAgain) {
      try {
        localStorage.setItem(dismissalKey(notification), "1");
      } catch {
        // localStorage unavailable — ignore
      }
    }
    onClose();
  };

  const handleLink = () => {
    if (notification.link) {
      openUrl(notification.link).catch(console.error);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Megaphone className="w-5 h-5 text-[var(--color-accent)]" />
              {title}
            </CardTitle>
            <Button variant="ghost" size="icon" onClick={handleClose} className="h-8 w-8">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {notification.image && (
            <img
              src={notification.image}
              alt="Notification"
              className="w-full h-auto rounded-[var(--radius-sm)] object-cover"
            />
          )}

          <p className="text-sm text-[var(--color-text-secondary)]">
            {notification.message}
          </p>

          {notification.link && (
            <Button onClick={handleLink} className="w-full gap-2">
              <ExternalLink className="w-4 h-4" />
              {notification.link_text || "Open Link"}
            </Button>
          )}

          <label className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] cursor-pointer select-none pt-1">
            <input
              type="checkbox"
              checked={dontShowAgain}
              onChange={(e) => setDontShowAgain(e.target.checked)}
              className="h-4 w-4 rounded border-[var(--color-border)] accent-[var(--color-accent)]"
            />
            Jangan tampilkan lagi
          </label>
        </CardContent>
      </Card>
    </div>
  );
}
