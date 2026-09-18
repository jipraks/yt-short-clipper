import { create } from "zustand";
import type { LatestVersionResponse } from "@/hooks/versionCheck";

type Theme = "light" | "dark";

interface AppState {
  sidebarCollapsed: boolean;
  availableUpdate: LatestVersionResponse | null;
  showLogs: boolean;
  theme: Theme;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setAvailableUpdate: (update: LatestVersionResponse | null) => void;
  toggleShowLogs: () => void;
  setTheme: (theme: Theme) => void;
}

function applyTheme(t: Theme) {
  document.documentElement.classList.toggle("dark", t === "dark");
}

function initTheme(): Theme {
  const stored = localStorage.getItem("app-theme") as Theme | null;
  if (stored === "dark" || stored === "light") return stored;
  // Respect system preference on first run
  if (window.matchMedia("(prefers-color-scheme: dark)").matches) return "dark";
  return "light";
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: localStorage.getItem("sidebar-collapsed") === "true",
  availableUpdate: null,
  showLogs: localStorage.getItem("app-show-logs") !== "off", // default on
  theme: (() => { const t = initTheme(); applyTheme(t); return t; })(),

  toggleSidebar: () =>
    set((state) => {
      const next = !state.sidebarCollapsed;
      localStorage.setItem("sidebar-collapsed", String(next));
      return { sidebarCollapsed: next };
    }),
  setSidebarCollapsed: (collapsed) => {
    localStorage.setItem("sidebar-collapsed", String(collapsed));
    set({ sidebarCollapsed: collapsed });
  },
  setAvailableUpdate: (update) => set({ availableUpdate: update }),

  toggleShowLogs: () =>
    set((state) => {
      const next = !state.showLogs;
      localStorage.setItem("app-show-logs", next ? "on" : "off");
      return { showLogs: next };
    }),

  setTheme: (theme: Theme) => {
    localStorage.setItem("app-theme", theme);
    applyTheme(theme);
    set({ theme });
  },
}));
