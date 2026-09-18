import { create } from "zustand";
import type { ProcessOptions } from "@/hooks/processClips";

export interface ClipLogLine {
  level: "info" | "error" | "success";
  message: string;
  ts: number;
}

interface ClipSessionInput {
  url: string;
  highlights: unknown[];
  sessionDir: string;
  options: ProcessOptions;
}

interface ProcessingClipsState extends ClipSessionInput {
  /** Session present (either completed, running, or failed). */
  initialized: boolean;
  logLines: ClipLogLine[];
  currentStep: number; // 0=download, 1=portrait, 2=hook, 3=caption, 4=watermark
  progress: number;
  isComplete: boolean;
  error: string | null;
  /** process_clips invoke is still running in the sidecar. */
  active: boolean;

  start: (input: ClipSessionInput) => void;
  appendLog: (message: string) => void;
  setStep: (step: number) => void;
  setProgress: (p: number) => void;
  setActive: (active: boolean) => void;
  setComplete: () => void;
  setError: (err: string) => void;
  /** Back to Create — clears the session so a fresh run starts clean. */
  reset: () => void;
}

const INITIAL: Omit<
  ProcessingClipsState,
  "url" | "highlights" | "sessionDir" | "options" | "start" | "appendLog" | "setStep" | "setProgress" | "setActive" | "setComplete" | "setError" | "reset"
> = {
  initialized: false,
  logLines: [],
  currentStep: 0,
  progress: 0,
  isComplete: false,
  error: null,
  active: false,
};

export const useProcessingClipsStore = create<ProcessingClipsState>((set) => ({
  url: "",
  highlights: [],
  sessionDir: "",
  options: {
    addCaptions: false,
    addHook: false,
    addWatermark: false,
    addCreditWatermark: false,
    reframeMode: "face",
    centeredBackground: "black",
    downloadQuality: "720p",
  },
  ...INITIAL,

  start: (input) =>
    set({
      ...input,
      initialized: true,
      logLines: [],
      currentStep: 0,
      progress: 0,
      isComplete: false,
      error: null,
      active: true,
    }),

  appendLog: (message) =>
    set((state) => {
      const m = message.toLowerCase();
      const level: ClipLogLine["level"] =
        m.includes("error") || m.includes("failed") ? "error"
          : m.includes("success") || m.includes("complete") || m.includes("saved") ? "success"
          : "info";
      const next = [...state.logLines, { level, message, ts: Date.now() }];
      // Never let the store grow unbounded on long sessions
      if (next.length > 5000) next.splice(0, next.length - 5000);
      return { logLines: next };
    }),

  setStep: (step) => set({ currentStep: step }),
  setProgress: (p) => set({ progress: p }),
  setActive: (active) => set({ active }),
  setComplete: () => set({ isComplete: true, active: false, progress: 100 }),
  setError: (err) => set({ error: err, active: false }),

  reset: () =>
    set({
      url: "",
      highlights: [],
      sessionDir: "",
      initialized: false,
      logLines: [],
      currentStep: 0,
      progress: 0,
      isComplete: false,
      error: null,
      active: false,
    }),
}));