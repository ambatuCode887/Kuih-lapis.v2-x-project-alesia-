"use client";

import { useState } from "react";
import { Clock } from "lucide-react";
import { riskBand } from "@/lib/check/assessment";
import type { HistoryEntry } from "@/lib/check/history";

interface HistoryListProps {
  entries: HistoryEntry[];
  activeId: string | null;
  onOpen: (id: string) => void;
  onClear: () => void;
}

function when(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function HistoryList({ entries, activeId, onOpen, onClear }: HistoryListProps) {
  const [confirming, setConfirming] = useState(false);

  return (
    <section aria-labelledby="recent-title" className="glass rounded-3xl p-5">
      <h2 id="recent-title" className="flex items-center gap-2 text-lg font-bold">
        <Clock aria-hidden size={20} className="text-jade-text" />
        Recent checks
      </h2>

      {entries.length === 0 ? (
        <p className="mt-3 text-ink-2">Your checks will appear here. They stay in this browser only.</p>
      ) : (
        <>
          <ul className="mt-3 space-y-1.5">
            {entries.map((entry) => {
              const band = entry.assessment
                ? riskBand(entry.assessment.risk_level, entry.assessment.risk_score)
                : null;
              const active = entry.id === activeId;
              return (
                <li key={entry.id}>
                  <button
                    type="button"
                    onClick={() => onOpen(entry.id)}
                    aria-current={active ? "true" : undefined}
                    className={`flex min-h-14 w-full items-center gap-3 rounded-2xl px-3 py-2 text-left transition-colors hover:bg-paper/70 ${
                      active ? "bg-paper/70 shadow-[inset_4px_0_0_var(--pine)]" : ""
                    }`}
                  >
                    {band ? (
                      <span
                        className="grid h-8 min-w-9 shrink-0 place-items-center rounded-lg px-1.5 text-sm font-extrabold text-on-jade"
                        style={{ background: band.color, color: "var(--paper)" }}
                        title={`${band.label} risk`}
                      >
                        {entry.assessment?.risk_score ?? "–"}
                      </span>
                    ) : (
                      <span
                        className="grid h-8 min-w-9 shrink-0 place-items-center rounded-lg px-1.5 text-sm font-extrabold text-ink-2 shadow-[inset_0_0_0_2px_var(--line-strong)]"
                        title="Question"
                      >
                        Q
                      </span>
                    )}
                    <span className="min-w-0">
                      <span className="block truncate font-semibold">{entry.title}</span>
                      <span className="block text-sm text-ink-2">{when(entry.at)}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>

          {confirming ? (
            <div role="group" aria-label="Confirm clearing" className="mt-4 space-y-2 rounded-2xl border-2 border-line-strong p-3">
              <p className="font-bold">Delete all recent checks?</p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    onClear();
                    setConfirming(false);
                  }}
                  className="min-h-11 rounded-full border-2 border-danger px-4 font-bold text-danger"
                >
                  Yes, delete
                </button>
                <button
                  type="button"
                  onClick={() => setConfirming(false)}
                  className="min-h-11 rounded-full border-2 border-line-strong px-4 font-semibold"
                >
                  Keep them
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setConfirming(true)}
              className="mt-4 min-h-11 rounded-full px-3 text-ink-2 underline underline-offset-4 hover:text-danger"
            >
              Clear history
            </button>
          )}
        </>
      )}
    </section>
  );
}
