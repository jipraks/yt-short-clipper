import "i18next";
import type { en } from "./locales/en";

// Type-check translation keys against the English messages, so a typo in t("...")
// fails the build instead of showing a raw key.
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation";
    resources: { translation: typeof en };
  }
}
