import type { Assessment } from "./assessment";
import type { CheckMode } from "./api";

/** One finished check, kept in this browser only. Screenshots are never saved. */
export interface HistoryEntry {
  id: string;
  /** ISO time the check finished. */
  at: string;
  mode: CheckMode;
  /** Short label for the list. */
  title: string;
  /** What the user pasted, for showing findings marked on it. */
  sourceText?: string;
  assessment: Assessment | null;
  text: string;
}

const KEY = "cyber-assistant-history-v1";
const MAX_ENTRIES = 30;

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function saveHistory(entries: HistoryEntry[]): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(entries.slice(0, MAX_ENTRIES)));
  } catch {
    // Private mode or a full disk: the page still works, it just forgets.
  }
}

export function clearHistory(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // nothing to do
  }
}
