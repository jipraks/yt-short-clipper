import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { saveCookies } from "@/hooks/cookies";

const EXTENSION_URL =
  "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc";
const YOUTUBE_URL = "https://www.youtube.com";

/** How long the success line stays up before the dialog closes itself. */
const SUCCESS_CLOSE_MS = 1200;

interface CookiesDialogProps {
  onDone: (valid: boolean) => void;
}

type UploadState =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "valid" }
  | { kind: "error"; message: string };

/** Replaces the saved YouTube cookies file, with the same checks and copy as the setup step. */
export function CookiesDialog({ onDone }: CookiesDialogProps) {
  const { t } = useTranslation();
  const fileRef = useRef<HTMLInputElement>(null);
  const [upload, setUpload] = useState<UploadState>({ kind: "idle" });
  const valid = upload.kind === "valid";
  const validRef = useRef(false);
  validRef.current = valid;
  // Stable, so Modal's close (and the auto-close timer) is not rebuilt on every render.
  const handleClose = useCallback(() => onDone(validRef.current), [onDone]);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // let the same file be picked again after a fix
    if (!file) return;
    setUpload({ kind: "checking" });

    let content: string;
    try {
      content = await file.text();
    } catch {
      setUpload({ kind: "error", message: t("onboardingCookies.errors.readFailed") });
      return;
    }

    // Name the likely mistake before asking the backend.
    const start = content.trimStart();
    if (start.startsWith("[") || start.startsWith("{")) {
      setUpload({ kind: "error", message: t("onboardingCookies.errors.wrongFormat") });
      return;
    }
    if (!content.includes("youtube.com")) {
      setUpload({ kind: "error", message: t("onboardingCookies.errors.notYoutube") });
      return;
    }

    try {
      const status = await saveCookies(content);
      setUpload(
        status.valid
          ? { kind: "valid" }
          : { kind: "error", message: t("onboardingCookies.errors.notSignedIn") },
      );
    } catch (err) {
      setUpload({ kind: "error", message: t("onboardingCookies.errors.saveFailed", { reason: String(err) }) });
    }
  };

  const link = (url: string) => () => {
    openUrl(url).catch(console.error);
  };

  const steps: { title: string; body: string; action?: { label: string; url: string } }[] = [
    {
      title: t("onboardingCookies.steps.install.title"),
      body: t("onboardingCookies.steps.install.body"),
      action: { label: t("onboardingCookies.steps.install.action"), url: EXTENSION_URL },
    },
    {
      title: t("onboardingCookies.steps.login.title"),
      body: t("onboardingCookies.steps.login.body"),
      action: { label: t("onboardingCookies.steps.login.action"), url: YOUTUBE_URL },
    },
    { title: t("onboardingCookies.steps.export.title"), body: t("onboardingCookies.steps.export.body") },
    { title: t("onboardingCookies.steps.upload.title"), body: t("onboardingCookies.steps.upload.body") },
  ];

  return (
    <Modal
      title={t("onboardingCookies.title")}
      closeLabel={t("dialogs.cookies.close")}
      onClose={handleClose}
      className="max-w-lg max-h-[90vh] overflow-y-auto"
    >
      {(close) => (
        <>
          {valid && <AutoClose close={close} />}
          <p className="mt-2 text-sm text-[var(--color-text-secondary)] leading-relaxed">{t("dialogs.cookies.lead")}</p>
          <p className="mt-2 text-xs text-[var(--color-text-muted)] leading-relaxed">{t("onboardingCookies.privacy")}</p>

          <h3 className="mt-6 text-sm font-semibold text-[var(--color-text-primary)]">{t("dialogs.cookies.stepsTitle")}</h3>
          <ol className="mt-3 space-y-4">
            {steps.map((step, i) => (
              <li key={step.title} className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-x-2">
                <span aria-hidden className="text-sm font-bold tabular-nums text-[var(--color-accent)]">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">{step.title}</p>
                  <p className="mt-0.5 text-sm text-[var(--color-text-secondary)] leading-relaxed">{step.body}</p>
                  {step.action && (
                    <button
                      type="button"
                      onClick={link(step.action.url)}
                      className="-ml-1 mt-1 inline-flex min-h-9 items-center rounded-[var(--radius-sm)] px-1 text-sm font-medium text-[var(--color-accent)] hover:underline cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border-focus)]"
                    >
                      {step.action.label}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ol>

          <input ref={fileRef} type="file" accept=".txt,text/plain" onChange={onFile} className="sr-only" tabIndex={-1} />
          <Button
            disabled={upload.kind === "checking" || valid}
            onClick={() => fileRef.current?.click()}
            className="mt-6 h-11 w-full"
          >
            {upload.kind === "checking"
              ? t("onboardingCookies.checking")
              : upload.kind === "error"
                ? t("onboardingCookies.chooseAgain")
                : t("onboardingCookies.choose")}
          </Button>

          <div aria-live="polite" className="mt-3">
            {valid && <p className="text-sm font-medium text-[var(--color-success)]">{t("onboardingCookies.valid")}</p>}
          </div>
          {upload.kind === "error" && (
            <p role="alert" className="text-sm text-[var(--color-error)] leading-relaxed">
              {upload.message}
            </p>
          )}
        </>
      )}
    </Modal>
  );
}

function AutoClose({ close }: { close: () => void }) {
  useEffect(() => {
    const id = setTimeout(close, SUCCESS_CLOSE_MS);
    return () => clearTimeout(id);
  }, [close]);
  return null;
}
