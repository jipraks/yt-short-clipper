import { useTranslation } from "react-i18next";
import { ExternalLink } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import type { NotificationResponse } from "@/hooks/notificationCheck";

interface NotificationDialogProps {
  notification: NotificationResponse;
  onClose: () => void;
  title?: string;
}

/** A notice sent by the server. Its message, image, and link text are shown as they arrive. */
export function NotificationDialog({ notification, onClose, title }: NotificationDialogProps) {
  const { t } = useTranslation();

  const handleLink = () => {
    if (notification.link) {
      openUrl(notification.link).catch(console.error);
    }
  };

  return (
    <Modal
      title={title ?? t("dialogs.notification.title")}
      closeLabel={t("dialogs.notification.close")}
      onClose={onClose}
      className="max-h-[90vh] overflow-y-auto"
    >
      {() => (
        <>
          {notification.image && (
            <img
              src={notification.image}
              alt={t("dialogs.notification.imageAlt")}
              className="mt-4 h-auto w-full rounded-[var(--radius)] object-cover"
            />
          )}

          <p className="mt-4 whitespace-pre-line text-sm text-[var(--color-text-secondary)] leading-relaxed">
            {notification.message}
          </p>

          {notification.link && (
            <Button onClick={handleLink} className="mt-6 h-11 w-full gap-2">
              <ExternalLink aria-hidden className="h-4 w-4" />
              {notification.link_text || t("dialogs.notification.openLink")}
            </Button>
          )}
        </>
      )}
    </Modal>
  );
}
