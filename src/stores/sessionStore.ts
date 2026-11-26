import { create } from "zustand";
import { invoke } from "@tauri-apps/api/core";
import type { Highlight, SessionData } from "@/hooks/highlights";
import { parseTimestamp, toTimestamp } from "@/lib/timecode";

export type SessionOrigin = "create" | "library";

export interface HighlightTrim {
  start: number;
  end: number;
  /** Transcript text for the new range, when the transcript is loaded. */
  transcriptText?: string;
}

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
  /** Move a highlight's start/end; the AI's original times are kept for reset. */
  trimHighlight: (index: number, trim: HighlightTrim) => void;
  /** Put a highlight back to the AI's original start/end. */
  resetHighlight: (index: number, transcriptText?: string) => void;
}

let saveTimer: ReturnType<typeof setTimeout> | undefined;

/** Write the highlights back to session_data.json, coalescing rapid drags. */
function scheduleSave(session: SessionData) {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    invoke("save_session_highlights", {
      sessionDir: session.session_dir,
      highlights: session.highlights,
    }).catch((err) => console.error("Failed to save trimmed highlights:", err));
  }, 600);
}

function withHighlight(
  session: SessionData,
  index: number,
  update: (h: Highlight) => Highlight,
): SessionData {
  const highlights = session.highlights.map((h, i) => (i === index ? update(h) : h));
  return { ...session, highlights };
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

  trimHighlight: (index, { start, end, transcriptText }) => {
    const { session } = get();
    if (!session) return;
    const next = withHighlight(session, index, (h) => ({
      ...h,
      original_start_time: h.original_start_time ?? h.start_time,
      original_end_time: h.original_end_time ?? h.end_time,
      start_time: toTimestamp(start),
      end_time: toTimestamp(end),
      duration_seconds: Math.round((end - start) * 10) / 10,
      ...(transcriptText !== undefined ? { transcript_text: transcriptText } : {}),
    }));
    set({ session: next });
    scheduleSave(next);
  },

  resetHighlight: (index, transcriptText) => {
    const { session } = get();
    if (!session) return;
    const next = withHighlight(session, index, (h) => {
      if (!h.original_start_time || !h.original_end_time) return h;
      const { original_start_time, original_end_time, ...rest } = h;
      return {
        ...rest,
        start_time: original_start_time,
        end_time: original_end_time,
        duration_seconds:
          Math.round((parseTimestamp(original_end_time) - parseTimestamp(original_start_time)) * 10) / 10,
        ...(transcriptText !== undefined ? { transcript_text: transcriptText } : {}),
      };
    });
    set({ session: next });
    scheduleSave(next);
  },
}));

