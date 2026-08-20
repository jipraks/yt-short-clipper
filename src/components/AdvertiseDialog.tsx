import { useState } from "react";
import { Check, Copy, Mail, Megaphone, X } from "lucide-react";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export const ADS_EMAIL = "ads@ytclip.org";

interface AdvertiseDialogProps {
  onClose: () => void;
}

export function AdvertiseDialog({ onClose }: AdvertiseDialogProps) {
  const [copied, setCopied] = useState(false);

  const copyEmail = async () => {
    try {
      await navigator.clipboard.writeText(ADS_EMAIL);
      setCopied(true);
      toast.success("Email address copied");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Could not copy the address");
    }
  };

  // Opens the user's mail client with a draft. It composes; it never sends.
  const composeEmail = () => {
    const subject = encodeURIComponent("Link placement in YT Short Clipper");
    openUrl(`mailto:${ADS_EMAIL}?subject=${subject}`).catch(() => {
      toast.error(`No mail app found — email us at ${ADS_EMAIL}`);
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Megaphone className="w-5 h-5 text-[var(--color-accent)]" />
              Put your link here
            </CardTitle>
            <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-[var(--color-text-secondary)]">
            The links in the sidebar are open for placement. If you have a product,
            service, or community that creators here would find useful, we would like to
            hear about it.
          </p>

          <div className="space-y-1.5">
            <p className="text-xs text-[var(--color-text-muted)]">
              Send us the details by email:
            </p>
            <div className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-bg-input)]">
              <span className="font-mono text-sm text-[var(--color-text-primary)] truncate">
                {ADS_EMAIL}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={copyEmail}
                className="h-7 gap-1.5 text-xs shrink-0"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[var(--color-success)]" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Copy
                  </>
                )}
              </Button>
            </div>
          </div>

          <p className="text-xs text-[var(--color-text-muted)]">
            Tell us what you are offering, the link you want listed, and how long you would
            like it up. We reply to every message.
          </p>

          <Button onClick={composeEmail} className="w-full gap-2">
            <Mail className="w-4 h-4" />
            Email {ADS_EMAIL}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
