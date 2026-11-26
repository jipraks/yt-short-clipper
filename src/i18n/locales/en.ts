/**
 * English strings, the reference for every other locale: `id.ts` must have the
 * same keys, which the compiler checks.
 *
 * Strings move here page by page as each page is redesigned; pages not yet
 * redesigned still hold their English text inline.
 */
export const en = {
  common: {
    appName: "Cuplik",
    language: {
      id: "Bahasa Indonesia",
      en: "English",
    },
  },
  languagePicker: {
    // Shown under this language's own option, so it is always in English.
    optionHint: "Menus and guides in English.",
    confirm: "Use English",
    saving: "Saving…",
    saveFailed: "Your language could not be saved. Try again.",
  },
  onboardingCookies: {
    title: "Connect YouTube to Cuplik",
    lead: "Cuplik downloads YouTube videos with your own account, using a cookies file from Chrome. You only do this once.",
    privacy: "The file holds your YouTube login. Cuplik keeps it on this computer and only uses it to talk to YouTube.",
    stepLabel: "Step {{n}}",
    steps: {
      install: {
        title: "Install the Get cookies.txt LOCALLY extension",
        body: "Open its page in the Chrome Web Store, then click Add to Chrome.",
        action: "Open the Chrome Web Store",
        alt: "Chrome Web Store page for Get cookies.txt LOCALLY with the Add to Chrome button",
      },
      allow: {
        title: "Allow the extension",
        body: "Chrome asks for permission. Click Add extension.",
        alt: "Chrome dialog asking to add Get cookies.txt LOCALLY, with the Add extension button",
      },
      login: {
        title: "Open YouTube and check you are signed in",
        body: "Open youtube.com in Chrome. If you see a Sign in button at the top right, sign in first.",
        action: "Open YouTube",
      },
      export: {
        title: "Export the cookies",
        body: "On the YouTube tab, click the extension icon at the top right of Chrome. If you can't see it, click the puzzle icon first. Check that the title says youtube.com, then click Export.",
        alt: "The extension open on youtube.com, with the Export button",
      },
      upload: {
        title: "Upload cookies.txt here",
        body: "Chrome saves a file called cookies.txt, usually in your Downloads folder.",
        alt: "Chrome download bubble showing cookies.txt",
      },
    },
    choose: "Choose cookies.txt",
    chooseAgain: "Choose another file",
    checking: "Checking the file…",
    valid: "YouTube is connected. Cuplik can download videos now.",
    alreadyValid: "YouTube is already connected. Upload a new file only if downloads start failing.",
    errors: {
      wrongFormat: "This file is in JSON format. In the extension, set Export Format to Netscape and export again.",
      notYoutube: "This file has no YouTube cookies. Export it from a youtube.com tab.",
      notSignedIn: "This file has YouTube cookies but no login. Sign in to YouTube in Chrome and export again.",
      readFailed: "The file could not be read. Try choosing it again.",
      saveFailed: "The cookies could not be saved: {{reason}}",
    },
    finish: "Start using Cuplik",
    finishing: "Saving…",
    finishFailed: "Your progress could not be saved. Try again.",
    later: "Do this later",
    laterHint: "Cuplik can't download videos until YouTube is connected. You can do it later from the Create page.",
  },
};
