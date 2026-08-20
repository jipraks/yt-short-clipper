import { X, Megaphone, ExternalLink } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { NotificationResponse } from "@/hooks/notificationCheck";

interface NotificationDialogProps {
  notification: NotificationResponse;
  onClose: () => void;
  title?: string;
}

export function NotificationDialog({ notification, onClose, title = "Announcement" }: NotificationDialogProps) {
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
            <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
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
        </CardContent>
      </Card>
    </div>
  );
}
