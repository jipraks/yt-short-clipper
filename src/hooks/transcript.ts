import { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { parseTimestamp } from "@/lib/timecode";

/** One timed piece of speech: a word from words.json, or a whole SRT line. */
export interface TimedToken {
  text: string;
  start: number;
  end: number;
}

export interface Transcript {
  tokens: TimedToken[];
  /** "word" when word timing is available, "line" for SRT fallback. */
  granularity: "word" | "line";
}

async function readText(path: string): Promise<string | null> {
  try {
    const res = await fetch(convertFileSrc(path));
    return res.ok ? await res.text() : null;
  } catch {
    return null;
  }
}

function parseWords(raw: string): TimedToken[] | null {
  try {
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return null;
    const tokens = data
      .filter((w) => typeof w?.word === "string" && typeof w?.start === "number")
      .map((w) => ({ text: w.word as string, start: w.start as number, end: (w.end ?? w.start) as number }));
    return tokens.length ? tokens : null;
  } catch {
    return null;
  }
}

function parseSrt(raw: string): TimedToken[] {
  const tokens: TimedToken[] = [];
  for (const block of raw.replace(/\r/g, "").split(/\n\n+/)) {
    const lines = block.trim().split("\n");
    const timeIdx = lines.findIndex((l) => l.includes("-->"));
    if (timeIdx < 0) continue;
    const [a, b] = lines[timeIdx].split("-->").map((s) => s.trim().split(" ")[0]);
    const text = lines
      .slice(timeIdx + 1)
      .join(" ")
      .replace(/<[^>]+>/g, "")
      .trim();
    if (text) tokens.push({ text, start: parseTimestamp(a), end: parseTimestamp(b) });
  }
  return tokens;
}

function sessionWordsPath(sessionDir: string, wordsPath?: string | null): string {
  return wordsPath || `${sessionDir}\\words.json`;
}

/**
 * Load the session's timed transcript: word timing from words.json when the
 * video had an original subtitle track, otherwise the SRT's lines.
 */
export function useTranscript(
  sessionDir: string,
  srtPath: string,
  wordsPath?: string | null,
): Transcript | null {
  const [transcript, setTranscript] = useState<Transcript | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const wordsRaw = await readText(sessionWordsPath(sessionDir, wordsPath));
      const words = wordsRaw ? parseWords(wordsRaw) : null;
      if (words) {
        if (!cancelled) setTranscript({ tokens: words, granularity: "word" });
        return;
      }
      const srtRaw = srtPath ? await readText(srtPath) : null;
      if (!cancelled) {
        setTranscript({ tokens: srtRaw ? parseSrt(srtRaw) : [], granularity: "line" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionDir, srtPath, wordsPath]);

  return transcript;
}

/** Tokens that overlap [start, end). */
export function tokensInRange(tokens: TimedToken[], start: number, end: number): TimedToken[] {
  return tokens.filter((t) => t.end > start && t.start < end);
}

export function textInRange(tokens: TimedToken[], start: number, end: number): string {
  return tokensInRange(tokens, start, end)
    .map((t) => t.text)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}
