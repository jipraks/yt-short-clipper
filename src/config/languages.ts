/**
 * Languages the AI can write clip titles, descriptions and hook text in.
 *
 * Mirrors LANG_NAMES in yt_short_clipper_core/constants.py — keep the two in
 * sync. The backend resolves the final name, so an entry missing here only
 * costs the user a dropdown option, never correctness.
 */
export interface OutputLanguage {
  code: string;
  name: string;
}

export const OUTPUT_LANGUAGES: OutputLanguage[] = [
  { code: "ar", name: "Arabic" },
  { code: "zh", name: "Chinese" },
  { code: "nl", name: "Dutch" },
  { code: "en", name: "English" },
  { code: "fr", name: "French" },
  { code: "de", name: "German" },
  { code: "hi", name: "Hindi" },
  { code: "id", name: "Indonesian" },
  { code: "it", name: "Italian" },
  { code: "ja", name: "Japanese" },
  { code: "ko", name: "Korean" },
  { code: "pl", name: "Polish" },
  { code: "pt", name: "Portuguese" },
  { code: "ru", name: "Russian" },
  { code: "es", name: "Spanish" },
  { code: "th", name: "Thai" },
  { code: "tr", name: "Turkish" },
  { code: "vi", name: "Vietnamese" },
];

/** "auto" means: write in whatever language the video is in. */
export const AUTO_LANGUAGE = "auto";

/**
 * Name for a subtitle code, or null when we cannot name it. Handles the
 * suffixed forms YouTube returns: "id-orig", "pt-BR", "en_US".
 */
export function languageNameForCode(code: string | null | undefined): string | null {
  if (!code) return null;
  const base = code.trim().toLowerCase().replace(/_/g, "-").split("-")[0];
  return OUTPUT_LANGUAGES.find((lang) => lang.code === base)?.name ?? null;
}
