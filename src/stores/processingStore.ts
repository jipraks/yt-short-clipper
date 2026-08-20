import { create } from "zustand";
import type { AIRequestSettings } from "@/hooks/highlights";

export interface Step {
  label: string;
  status: "pending" | "running" | "done" | "error";
}

export interface LogLine {
  level: "info" | "warn" | "error" | "success";
  message: string;
  ts: number;
}

export interface FindHighlightsRequest {
  url: string;
  numClips: number;
  subtitleLanguage: string;
  ai: AIRequestSettings;
  /** Optional free-text steer for the highlight prompt. */
  userDirection?: string;
  /** Language code for titles and hooks, or "auto" to follow the video. */
  outputLanguage?: string;
}

interface ProcessingState {
  isProcessing: boolean;
  steps: Step[];
  logLines: LogLine[];
  error: string | null;
  request: FindHighlightsRequest | null;
  start: (request: FindHighlightsRequest) => void;
  updateStep: (index: number, status: Step["status"]) => void;
  appendLog: (line: LogLine) => void;
  setError: (message: string) => void;
  finish: () => void;
  reset: () => void;
}

const DEFAULT_STEPS: Step[] = [
  { label: "Download subtitle", status: "pending" },
  { label: "Find highlights with AI", status: "pending" },
];

export const useProcessingStore = create<ProcessingState>((set) => ({
  isProcessing: false,
  steps: [...DEFAULT_STEPS],
  logLines: [],
  error: null,
  request: null,

  start: (request) =>
    set({
      isProcessing: true,
      steps: DEFAULT_STEPS.map((s) => ({ ...s })),
      logLines: [],
      error: null,
      request,
    }),

  updateStep: (index, status) =>
    set((state) => {
      const steps = [...state.steps];
      if (steps[index]) {
        steps[index] = { ...steps[index], status };
      }
      return { steps };
    }),

  appendLog: (line) => set((state) => ({ logLines: [...state.logLines, line] })),

  setError: (message) =>
    set((state) => ({
      error: message,
      isProcessing: false,
      steps: state.steps.map((s) =>
        s.status === "running" ? { ...s, status: "error" } : s
      ),
    })),

  finish: () =>
    set((state) => ({
      isProcessing: false,
      steps: state.steps.map((s) => ({ ...s, status: "done" })),
    })),

  reset: () =>
    set({
      isProcessing: false,
      steps: DEFAULT_STEPS.map((s) => ({ ...s })),
      logLines: [],
      error: null,
      request: null,
    }),
}));
