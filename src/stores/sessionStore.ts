import { create } from "zustand";
import type { Highlight, SessionData } from "@/hooks/highlights";

export type SessionOrigin = "create" | "library";

interface SessionState {
  session: SessionData | null;
  origin: SessionOrigin;
  selectedIndices: Set<number>;
  setSession: (session: SessionData, origin?: SessionOrigin) => void;
  clearSession: () => void;
  toggleSelected: (index: number) => void;
  selectAll: () => void;
  deselectAll: () => void;
  getSelectedHighlights: () => Highlight[];
}

export const useSessionStore = create<SessionState>((set, get) => ({
  session: null,
  origin: "create",
  selectedIndices: new Set(),

  setSession: (session, origin = "create") =>
    set({
      session,
      origin,
      selectedIndices: new Set(session.highlights.map((_, i) => i)),
    }),

  clearSession: () => set({ session: null, selectedIndices: new Set() }),

  toggleSelected: (index) =>
    set((state) => {
      const next = new Set(state.selectedIndices);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return { selectedIndices: next };
    }),

  selectAll: () =>
    set((state) => ({
      selectedIndices: new Set(state.session?.highlights.map((_, i) => i) ?? []),
    })),

  deselectAll: () => set({ selectedIndices: new Set() }),

  getSelectedHighlights: () => {
    const { session, selectedIndices } = get();
    if (!session) return [];
    return session.highlights.filter((_, i) => selectedIndices.has(i));
  },
}));
