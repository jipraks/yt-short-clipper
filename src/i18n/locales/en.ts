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
  onboarding: {
    stepLabel: "Step {{n}}",
    stepOf: "Step {{n}} of {{total}}",
    back: "Back",
    finish: "Start using Cuplik",
    next: "Next step",
    upNext: "Up next: {{title}}",
    lastStep: "Last step. After this you can start making clips.",
    finishFailed: "Your progress could not be saved. Try again.",
  },
  languagePicker: {
    // Shown under this language's own option, so it is always in English.
    optionHint: "Menus and guides in English.",
    confirm: "Use English",
    saving: "Saving…",
    saveFailed: "Your language could not be saved. Try again.",
    agreeBefore: "I agree to Cuplik's ",
    terms: "Terms and Conditions",
    agreeBetween: " and ",
    privacy: "Privacy Policy",
    agreeAfter: ".",
    agreeRequired: "Tick the box above to continue.",
  },
  onboardingCookies: {
    title: "Connect YouTube to Cuplik",
    lead: "Cuplik downloads YouTube videos with your own account, using a cookies file from Chrome. You only do this once.",
    privacy: "The file holds your YouTube login. Cuplik keeps it on this computer and only uses it to talk to YouTube.",
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
    later: "Skip for now",
    laterHint: "Cuplik can't download videos until YouTube is connected. You can do it later from the Create page.",
  },
  onboardingAi: {
    title: "Set up your AI balance",
    lead: "Cuplik uses AI to find the best moments in a video and to write each clip's title. The cost comes out of your Cuplik balance as you use it.",
    balance: "Balance",
    status: {
      loading: "Setting up your AI account…",
      inactive: "Your AI account is not active yet, usually because there was no internet. Check your connection and try again.",
      retry: "Try again",
      retrying: "Trying…",
      unsupported: "This version of Cuplik can no longer use the AI balance. Install the latest version first.",
      balanceLoading: "Loading your balance…",
      balanceFailed: "Your balance could not be loaded. Check your internet connection.",
      blocked: "This account has been disabled. Contact support@ytclip.org.",
    },
    steps: {
      backup: {
        title: "Save your Account Key",
        body: "The Account Key is the only way to get your balance back if you reinstall Cuplik or move to another computer. Keep it somewhere safe.",
        action: "Save Account Key",
        again: "Show the key again",
        done: "Your Account Key is saved.",
      },
      topup: {
        title: "Top up your balance",
        body: "Pay with QRIS from your bank or e-wallet app. You can skip this and top up when you are ready to process a video.",
        action: "Top up with QRIS",
      },
    },
    restoreQuestion: "Already have an Account Key from an earlier install?",
    restore: "Restore my balance",
    emptyHint: "Your balance is empty. You can top up any time from the Top Up button in the sidebar.",
  },
  onboardingRepliz: {
    title: "Post clips straight to your socials",
    lead: "Connect Cuplik to Repliz and a finished clip goes to YouTube, TikTok, Instagram and Facebook from inside Cuplik, right away or on a schedule.",
    benefits: {
      many: "Upload one clip to many accounts at once.",
      schedule: "Schedule posts without leaving Cuplik.",
      setup: "No Google Cloud Console or TikTok Developer setup.",
    },
    plan: {
      name: "Repliz Premium",
      why: "Cuplik needs Premium: uploading uses Repliz's Schedule API, which starts at Premium.",
      durationLabel: "Billing period",
      months_one: "{{count}} month",
      months_other: "{{count}} months",
      perMonth: "{{price}} a month",
      saving: "{{percent}}% less than paying monthly",
      features: {
        accounts: "75 accounts and 10 operators",
        scheduled: "Scheduled posts, including Status, Stories, Channels and groups on WhatsApp and Telegram, and boards on Pinterest",
        inbox: "DM inbox, comment inbox and reports",
        ai: "AI replies with your own key or Token Balance",
        research: "Threads and TikTok research",
      },
      priceNote: "Prices from Repliz as of 26 November 2026 and may change.",
      signup: "Sign up for Repliz",
    },
    connect: {
      title: "Connect your Repliz account",
      body: "Copy the Access Key and Secret Key from your Repliz dashboard and paste them here.",
      accessKey: "Access Key",
      secretKey: "Secret Key",
      show: "Show",
      hide: "Hide",
      action: "Connect and check accounts",
      checking: "Checking…",
      missing: "Fill in both keys first.",
      failed: "Repliz did not accept these keys: {{reason}}",
      saveFailed: "The keys worked but could not be saved. Try again.",
      connected_one: "Connected. Repliz has {{count}} social account ready:",
      connected_other: "Connected. Repliz has {{count}} social accounts ready:",
      noAccounts: "Connected, but no social account is linked in Repliz yet. Add one in your Repliz dashboard.",
      alreadyConnected: "Repliz is already connected. Paste new keys only to change accounts.",
    },
    skip: "Skip, set up Repliz later",
  },
};
