import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import { en } from "./locales/en";
import { id } from "./locales/id";

export const SUPPORTED_LANGUAGES = ["id", "en"] as const;

const HINT_KEY = "cuplik.language";

/**
 * The language to start in, before config.json has loaded: the last saved
 * choice if this webview remembers it, else the system language. config.json
 * stays the source of truth; this only keeps the first paint, and a reloaded
 * module, from showing the wrong language.
 */
function startLanguage(): "id" | "en" {
  try {
    const hint = localStorage.getItem(HINT_KEY);
    if (hint === "id" || hint === "en") return hint;
  } catch {
    // Storage unavailable: fall through to the system language.
  }
  return navigator.language.toLowerCase().startsWith("id") ? "id" : "en";
}

/** Called whenever the saved language is known, so the next start uses it. */
export function rememberLanguage(language: "id" | "en"): void {
  try {
    localStorage.setItem(HINT_KEY, language);
  } catch {
    // Only a hint; config.json still has the real value.
  }
}

void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    id: { translation: id },
  },
  lng: startLanguage(),
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
