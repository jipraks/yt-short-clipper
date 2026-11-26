import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Copy, Mail } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";

export const ADS_EMAIL = "ads@ytclip.org";

interface AdvertiseDialogProps {
  onClose: () => void;
}

/** How to get a link into the Help menu: one address, copy it or open a draft. */
export function AdvertiseDialog({ onClose }: AdvertiseDialogProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const copyEmail = async () => {
    try {
      await navigator.clipboard.writeText(ADS_EMAIL);
      setCopied(true);
      toast.success(t("advertise.copyDone"));
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error(t("advertise.copyFailed"));
    }
  };

  // Opens the user's mail client with a draft. It composes; it never sends.
  const composeEmail = () => {
    const subject = encodeURIComponent(t("advertise.subject"));
    openUrl(`mailto:${ADS_EMAIL}?subject=${subject}`).catch(() => {
      toast.error(t("advertise.noMailApp", { email: ADS_EMAIL }));
    });
  };

  return (
    <Modal title={t("advertise.title")} closeLabel={t("advertise.close")} onClose={onClose}>
      {() => (
        <>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("advertise.body")}</p>

          <p className="mt-5 mb-1.5 text-xs font-medium text-[var(--color-text-muted)]">{t("advertise.emailLabel")}</p>
          <div className="flex items-center justify-between gap-2 rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg-input)] py-1.5 pl-4 pr-1.5">
            <span className="truncate text-base font-semibold text-[var(--color-text-primary)]">{ADS_EMAIL}</span>
            <Button variant="ghost" onClick={() => void copyEmail()} className="h-9 shrink-0 gap-1.5 px-3">
              {copied ? <Check aria-hidden className="h-4 w-4 text-[var(--color-success)]" /> : <Copy aria-hidden className="h-4 w-4" />}
              {copied ? t("advertise.copied") : t("advertise.copy")}
            </Button>
          </div>
          <p className="mt-2 text-xs text-[var(--color-text-muted)] leading-relaxed">{t("advertise.what")}</p>

          <Button onClick={composeEmail} className="mt-6 h-11 w-full gap-2">
            <Mail aria-hidden className="h-4 w-4" />
            {t("advertise.compose")}
          </Button>
        </>
      )}
    </Modal>
  );
}
