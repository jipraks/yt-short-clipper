import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/brand/Wordmark";
import { getCookiesStatus, saveCookies } from "@/hooks/cookies";
import { useCookiesStore } from "@/stores/cookiesStore";
import { useConfigStore } from "@/stores/configStore";
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
export function CookiesStepPage() {
  const { t } = useTranslation();
  const completeOnboarding = useConfigStore((s) => s.completeOnboarding);
  const setCookiesStatus = useCookiesStore((s) => s.setCookiesStatus);
  const fileRef = useRef<HTMLInputElement>(null);
  const [upload, setUpload] = useState<UploadState>({ kind: "idle" });
  const [finishing, setFinishing] = useState<"idle" | "saving" | "error">("idle");

  // A returning user may already have working cookies.
  useEffect(() => {
    getCookiesStatus()
      .then((status) => {
        if (status.valid) setUpload((u) => (u.kind === "idle" ? { kind: "alreadyValid" } : u));
      })
      .catch(() => {});
  }, []);

  const connected = upload.kind === "valid" || upload.kind === "alreadyValid";

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

  const finish = async () => {
    setFinishing("saving");
    try {
      await completeOnboarding();
    } catch {
      setFinishing("error");
    }
  };

  const link = (url: string) => () => {
    openUrl(url).catch(console.error);
  };

  return (
    <main className="min-h-screen bg-[var(--color-bg-secondary)] px-4 py-10">
      <div className="mx-auto w-full max-w-[720px]">
        <Wordmark className="text-2xl" />

        <h1 className="mt-10 text-2xl font-bold text-[var(--color-text-primary)]">
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
              variant={connected ? "outline" : "default"}
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
          </Step>
        </ol>

        <div className="mt-10 border-t border-[var(--color-border-light)] pt-6">
          {finishing === "error" && (
            <p role="alert" className="mb-3 text-sm text-[var(--color-error)]">
              {t("onboardingCookies.finishFailed")}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              size="lg"
              disabled={!connected || finishing === "saving"}
              onClick={() => void finish()}
              className="h-12 px-6 text-base font-semibold"
            >
              {finishing === "saving" ? t("onboardingCookies.finishing") : t("onboardingCookies.finish")}
            </Button>
            {!connected && (
              <Button variant="ghost" size="lg" disabled={finishing === "saving"} onClick={() => void finish()} className="h-12">
                {t("onboardingCookies.later")}
              </Button>
            )}
          </div>
          {!connected && (
            <p className="mt-3 text-sm text-[var(--color-text-muted)] leading-relaxed">
              {t("onboardingCookies.laterHint")}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}

function Step({
  n,
  title,
  body,
  children,
}: {
  n: number;
  title: string;
  body: string;
  children?: React.ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <li className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3">
      <span aria-hidden className="pt-0.5 text-base font-bold tabular-nums text-[var(--color-accent)]">
        {n}
      </span>
      <div className="space-y-3">
        <div>
          <span className="sr-only">{t("onboardingCookies.stepLabel", { n })}: </span>
          <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)] leading-relaxed">{body}</p>
        </div>
        {children}
      </div>
    </li>
  );
}

/** A screenshot of the real Chrome screen, framed so it reads as a picture. */
function Shot({ src, alt, maxWidth }: { src: string; alt: string; maxWidth?: number }) {
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      style={maxWidth ? { maxWidth } : undefined}
      className="block w-full h-auto rounded-[var(--radius-sm)] border border-[var(--color-border)]"
    />
  );
}
