import { create } from "zustand";
import type { LatestVersionResponse } from "@/hooks/versionCheck";

interface AppState {
  availableUpdate: LatestVersionResponse | null;
  setAvailableUpdate: (update: LatestVersionResponse | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  availableUpdate: null,
  setAvailableUpdate: (update) => set({ availableUpdate: update }),
}));
