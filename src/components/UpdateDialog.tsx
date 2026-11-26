import { useTranslation } from "react-i18next";
import { ExternalLink } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import type { LatestVersionResponse } from "@/hooks/versionCheck";
import { APP_VERSION } from "@/config/version";

interface UpdateDialogProps {
  update: LatestVersionResponse;
  onClose: () => void;
}

export function UpdateDialog({ update, onClose }: UpdateDialogProps) {
  const { t } = useTranslation();

  const handleDownload = () => {
    openUrl(update.download_url).catch(console.error);
  };

  return (
    <Modal title={t("dialogs.update.title")} closeLabel={t("dialogs.update.close")} onClose={onClose}>
      {(close) => (
        <>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("dialogs.update.body")}</p>

          <dl className="mt-5 space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--color-text-muted)]">{t("dialogs.update.current")}</dt>
              <dd className="font-medium tabular-nums text-[var(--color-text-primary)]">{APP_VERSION}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-[var(--color-text-muted)]">{t("dialogs.update.latest")}</dt>
              <dd className="font-semibold tabular-nums text-[var(--color-text-primary)]">{update.version}</dd>
            </div>
          </dl>

          {update.changelog && (
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">{t("dialogs.update.whatsNew")}</h3>
              <p className="mt-1.5 max-h-48 overflow-y-auto whitespace-pre-line rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-input)] p-3 text-sm text-[var(--color-text-secondary)] leading-relaxed">
                {update.changelog}
              </p>
            </div>
          )}

          <div className="mt-6 flex justify-end gap-2">
            <Button variant="ghost" onClick={close} className="h-11 px-4">
              {t("dialogs.update.later")}
            </Button>
            <Button onClick={handleDownload} className="h-11 gap-2 px-5">
              <ExternalLink aria-hidden className="h-4 w-4" />
              {t("dialogs.update.download")}
            </Button>
          </div>
        </>
      )}
    </Modal>
  );
}
