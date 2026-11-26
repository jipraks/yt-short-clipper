/** English strings for the "replizSettings" namespace. Reference for id/replizSettings.ts. */
export const replizSettings = {
  title: "Repliz",
  subtitle: "Post finished clips to YouTube, TikTok, Instagram and Facebook without leaving Cuplik.",
  status: {
    loading: "Reading your saved keys…",
    checking: "Checking the connection to Repliz…",
    connected_one: "Connected. {{count}} social account is ready.",
    connected_other: "Connected. {{count}} social accounts are ready.",
    notConnected: "Not connected yet. Paste your Access Key and Secret Key below.",
    rejected: "Repliz rejected the saved keys: {{reason}}",
    rejectedHint: "Copy fresh keys from your Repliz dashboard and connect again.",
    accountOff: "not linked",
  },
  pitch: {
    title: "Why Repliz",
  },
  keys: {
    title: "Your Repliz keys",
    stored: "Cuplik keeps the keys in your system's credential store, not in a plain file.",
  },
  connected: "Repliz is connected.",
  dashboard: "Open Repliz dashboard",
  disconnect: {
    action: "Disconnect Repliz",
    title: "Disconnect Repliz?",
    body: "Cuplik removes the keys. Your accounts and scheduled posts in Repliz stay as they are. To connect again, paste the keys again.",
    confirm: "Disconnect",
    cancel: "Cancel",
    close: "Close",
    working: "Disconnecting…",
    done: "Repliz is disconnected.",
    failed: "Repliz could not be disconnected. Try again.",
  },
};
