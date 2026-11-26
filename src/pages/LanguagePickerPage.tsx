import { useState } from "react";
import i18n from "@/i18n";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/brand/Wordmark";
import { useConfigStore } from "@/stores/configStore";
import type { AppLanguage } from "@/hooks/appConfig";

const OPTIONS: AppLanguage[] = ["id", "en"];

/**
 * First-launch screen. Each option describes itself in its own language, and
 * the button speaks the selected one, so the user sees what they will get
 * before anything is saved.
 */
export function LanguagePickerPage() {
  const setLanguage = useConfigStore((s) => s.setLanguage);
  const [selected, setSelected] = useState<AppLanguage>(
    i18n.language === "id" ? "id" : "en",
  );
  const [state, setState] = useState<"idle" | "saving" | "error">("idle");

  const t = i18n.getFixedT(selected);

  const confirm = async () => {
    setState("saving");
    try {
      await setLanguage(selected);
    } catch {
      setState("error");
    }
  };

  return (
    <main className="min-h-screen bg-[var(--color-bg-secondary)] flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-[460px]">
        <Wordmark className="text-2xl" />

        <form
          className="mt-10"
          onSubmit={(e) => {
            e.preventDefault();
            void confirm();
          }}
        >
          <fieldset disabled={state === "saving"}>
            <legend className="text-2xl font-bold text-[var(--color-text-primary)]">
              Pilih bahasa
            </legend>
            <p className="mt-1 text-base text-[var(--color-text-secondary)]" lang="en">
              Choose your language
            </p>

            <div className="mt-6 space-y-3">
              {OPTIONS.map((lang) => {
                const checked = selected === lang;
                return (
                  <label
                    key={lang}
                    lang={lang}
                    className={`flex items-center gap-4 rounded-[var(--radius)] border px-4 py-4 cursor-pointer transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[var(--color-border-focus)] has-[:focus-visible]:ring-offset-2 ${
                      checked
                        ? "border-[var(--color-text-primary)] bg-[var(--color-bg-card)]"
                        : "border-[var(--color-border)] hover:bg-[var(--color-bg-primary)]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="language"
                      value={lang}
                      checked={checked}
                      onChange={() => {
                        setSelected(lang);
                        if (state === "error") setState("idle");
                      }}
                      className="sr-only"
                    />
                    <span
                      aria-hidden
                      className={`w-5 h-5 shrink-0 rounded-full border-2 flex items-center justify-center ${
                        checked ? "border-[var(--color-text-primary)]" : "border-[var(--color-text-muted)]"
                      }`}
                    >
                      {checked && <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-text-primary)]" />}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-base font-semibold text-[var(--color-text-primary)]">
                        {i18n.getFixedT(lang)(`common.language.${lang}`)}
                      </span>
                      <span className="block mt-0.5 text-sm text-[var(--color-text-secondary)]">
                        {i18n.getFixedT(lang)("languagePicker.optionHint")}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          {state === "error" && (
            <p role="alert" lang={selected} className="mt-4 text-sm text-[var(--color-error)]">
              {t("languagePicker.saveFailed")}
            </p>
          )}

          <Button
            type="submit"
            size="lg"
            lang={selected}
            disabled={state === "saving"}
            className="mt-6 w-full h-12 text-base font-semibold"
          >
            {state === "saving" ? t("languagePicker.saving") : t("languagePicker.confirm")}
          </Button>
        </form>
      </div>
    </main>
  );
}
