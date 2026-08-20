import { create } from "zustand";
import type { LatestVersionResponse } from "@/hooks/versionCheck";

interface AppState {
  sidebarCollapsed: boolean;
  availableUpdate: LatestVersionResponse | null;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setAvailableUpdate: (update: LatestVersionResponse | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: localStorage.getItem("sidebar-collapsed") === "true",
  availableUpdate: null,
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
}));
