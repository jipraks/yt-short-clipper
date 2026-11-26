import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Step, Shot } from "./Step";
import { getCookiesStatus, saveCookies } from "@/hooks/cookies";
import { useCookiesStore } from "@/stores/cookiesStore";
import storeImg from "@/assets/onboarding/cookies/store.webp";
import addExtensionImg from "@/assets/onboarding/cookies/add-extension.webp";
import exportImg from "@/assets/onboarding/cookies/export.webp";
import downloadedImg from "@/assets/onboarding/cookies/downloaded.webp";

const EXTENSION_URL =
  "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc";
const YOUTUBE_URL = "https://www.youtube.com";

type UploadState =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "valid" }
  | { kind: "alreadyValid" }
  | { kind: "error"; message: string };

/**
 * First-launch setup, step: connect YouTube. Walks a new user through getting
 * a cookies.txt out of Chrome and checks the file before it is saved.
 */
export function CookiesStepPage({ onReadyChange }: { onReadyChange: (ready: boolean) => void }) {
  const { t } = useTranslation();
  const setCookiesStatus = useCookiesStore((s) => s.setCookiesStatus);
  const fileRef = useRef<HTMLInputElement>(null);
  const [upload, setUpload] = useState<UploadState>({ kind: "idle" });

  // A returning user may already have working cookies.
  useEffect(() => {
    getCookiesStatus()
      .then((status) => {
        if (status.valid) setUpload((u) => (u.kind === "idle" ? { kind: "alreadyValid" } : u));
      })
      .catch(() => {});
  }, []);

  const connected = upload.kind === "valid" || upload.kind === "alreadyValid";
  useEffect(() => onReadyChange(connected), [connected, onReadyChange]);

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
      if (status.valid) {
        setCookiesStatus(true, true);
        setUpload({ kind: "valid" });
      } else {
        setUpload({ kind: "error", message: t("onboardingCookies.errors.notSignedIn") });
      }
    } catch (err) {
      setUpload({
        kind: "error",
        message: t("onboardingCookies.errors.saveFailed", { reason: String(err) }),
      });
    }
  };

  const link = (url: string) => () => {
    openUrl(url).catch(console.error);
  };

  return (
    <>
      <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">
        {t("onboardingCookies.title")}
      </h1>
      <p className="mt-2 text-base text-[var(--color-text-secondary)] leading-relaxed">
        {t("onboardingCookies.lead")}
      </p>
      <p className="mt-3 text-sm text-[var(--color-text-muted)] leading-relaxed">
        {t("onboardingCookies.privacy")}
      </p>

      <ol className="mt-8 space-y-8">
        <Step n={1} title={t("onboardingCookies.steps.install.title")} body={t("onboardingCookies.steps.install.body")}>
          <Button variant="outline" onClick={link(EXTENSION_URL)} className="h-11 px-4">
            {t("onboardingCookies.steps.install.action")}
          </Button>
          <Shot src={storeImg} alt={t("onboardingCookies.steps.install.alt")} />
        </Step>

        <Step n={2} title={t("onboardingCookies.steps.allow.title")} body={t("onboardingCookies.steps.allow.body")}>
          <Shot src={addExtensionImg} alt={t("onboardingCookies.steps.allow.alt")} maxWidth={360} />
        </Step>

        <Step n={3} title={t("onboardingCookies.steps.login.title")} body={t("onboardingCookies.steps.login.body")}>
          <Button variant="outline" onClick={link(YOUTUBE_URL)} className="h-11 px-4">
            {t("onboardingCookies.steps.login.action")}
          </Button>
        </Step>

        <Step n={4} title={t("onboardingCookies.steps.export.title")} body={t("onboardingCookies.steps.export.body")}>
          <Shot src={exportImg} alt={t("onboardingCookies.steps.export.alt")} maxWidth={420} />
        </Step>

        <Step n={5} title={t("onboardingCookies.steps.upload.title")} body={t("onboardingCookies.steps.upload.body")}>
          <Shot src={downloadedImg} alt={t("onboardingCookies.steps.upload.alt")} maxWidth={300} />

          <input ref={fileRef} type="file" accept=".txt,text/plain" onChange={onFile} className="sr-only" tabIndex={-1} />
          <Button
            variant="outline"
            disabled={upload.kind === "checking"}
            onClick={() => fileRef.current?.click()}
            className="h-11 px-5"
          >
            {upload.kind === "checking"
              ? t("onboardingCookies.checking")
              : connected
                ? t("onboardingCookies.chooseAgain")
                : t("onboardingCookies.choose")}
          </Button>

          <div aria-live="polite">
            {upload.kind === "valid" && (
              <p className="text-sm font-medium text-[var(--color-success)]">{t("onboardingCookies.valid")}</p>
            )}
            {upload.kind === "alreadyValid" && (
              <p className="text-sm text-[var(--color-success)]">{t("onboardingCookies.alreadyValid")}</p>
            )}
          </div>
          {upload.kind === "error" && (
            <p role="alert" className="text-sm text-[var(--color-error)] leading-relaxed">
              {upload.message}
            </p>
          )}
          {!connected && (
            <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">{t("onboardingCookies.laterHint")}</p>
          )}
        </Step>
      </ol>

    </>
  );
}
