import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "./locales/en";
import { id } from "./locales/id";

export const SUPPORTED_LANGUAGES = ["id", "en"] as const;

/**
 * Until the saved choice loads from config.json (or on first launch, before
 * the user picks), follow the system language.
 */
function systemLanguage(): "id" | "en" {
  return navigator.language.toLowerCase().startsWith("id") ? "id" : "en";
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    id: { translation: id },
  },
  lng: systemLanguage(),
  fallbackLng: "en",
  supportedLngs: SUPPORTED_LANGUAGES,
  // React already escapes rendered strings.
  interpolation: { escapeValue: false },
  returnNull: false,
});

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});
document.documentElement.lang = i18n.language;

export default i18n;
