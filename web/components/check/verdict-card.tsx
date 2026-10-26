"use client";

import { type CSSProperties } from "react";
import { Check, CircleQuestionMark, ShieldCheck, TriangleAlert } from "lucide-react";
import {
  highlightSegments,
  riskBand,
  type Assessment,
  type BandKey,
} from "@/lib/check/assessment";

// Plain-language headline for each risk band. It never promises that something is
// safe: a clean result only means no warning signs were found.
const HEADLINES: Record<BandKey, { title: string; sub: string }> = {
  critical: { title: "This looks like a scam", sub: "Do not reply, click or send anything." },
  high: { title: "This looks like a scam", sub: "Do not reply, click or send anything." },
  moderate: { title: "Be careful", sub: "Some things look suspicious." },
  low: {
    title: "No warning signs found",
    sub: "If you are unsure, check with the sender another way.",
  },
  unknown: {
    title: "Not sure",
    sub: "There is not enough to tell. Check with someone you trust.",
  },
};

const SCALE: { key: BandKey; label: string }[] = [
  { key: "low", label: "Low" },
  { key: "moderate", label: "Medium" },
  { key: "high", label: "High" },
  { key: "critical", label: "Very high" },
];

const SCALE_COLOR: Record<BandKey, string> = {
  low: "var(--risk-low)",
  moderate: "var(--risk-moderate)",
  high: "var(--risk-high)",
  critical: "var(--risk-critical)",
  unknown: "var(--ink-2)",
};

const MAX_STEPS = 3;

function VerdictIcon({ band }: { band: BandKey }) {
  const props = { "aria-hidden": true, size: 34, strokeWidth: 2.2 } as const;
  if (band === "low") return <ShieldCheck {...props} />;
  if (band === "unknown") return <CircleQuestionMark {...props} />;
  return <TriangleAlert {...props} />;
}

function Scale({ score, active }: { score: number | null; active: BandKey }) {
  return (
    <div role="img" aria-label={`Risk level: ${active}`}>
      <div className="relative grid grid-cols-4 gap-1">
        {SCALE.map((band) => (
          <span
            key={band.key}
            className="h-2.5 rounded-full"
            style={{
              background: SCALE_COLOR[band.key],
              opacity: band.key === active ? 1 : 0.28,
            }}
          />
        ))}
        {score !== null && (
          <span
            className="absolute -top-1.5 h-5 w-1 -translate-x-1/2 rounded-full bg-ink ring-2 ring-card"
            style={{ left: `${Math.min(100, Math.max(0, score))}%` }}
          />
        )}
      </div>
      <div className="mt-2 grid grid-cols-4 text-sm text-ink-2">
        {SCALE.map((band) => (
          <span key={band.key}>{band.label}</span>
        ))}
      </div>
    </div>
  );
}

interface VerdictCardProps {
  assessment: Assessment;
  /** What the person pasted, shown back with the warning signs marked. */
  sourceText?: string;
}

export function VerdictCard({ assessment, sourceText }: VerdictCardProps) {
  const band = riskBand(assessment.risk_level, assessment.risk_score);
  const headline = HEADLINES[band.key];
  const indicators = assessment.indicators ?? [];
  const steps = (assessment.recommended_actions ?? []).slice(0, MAX_STEPS);
  const segments = sourceText ? highlightSegments(sourceText, indicators) : [];
  const marked = new Set(segments.flatMap((s) => (s.mark ? [s.mark] : [])));
  const urgent = (assessment.risk_score ?? 0) >= 50;

  return (
    <article
      className="glass overflow-hidden rounded-3xl"
      style={
        {
          "--band": band.color,
          borderTopWidth: 6,
          borderTopColor: band.color,
        } as CSSProperties
      }
    >
      <header
        className="flex items-center gap-4 p-5 sm:p-6"
        style={{ background: "color-mix(in srgb, var(--band) 11%, transparent)" }}
      >
        <span
          className="grid size-16 shrink-0 place-items-center rounded-full"
          style={{
            color: band.color,
            boxShadow: `inset 0 0 0 2px ${band.color}`,
            background: "color-mix(in srgb, var(--band) 14%, transparent)",
          }}
        >
          <VerdictIcon band={band.key} />
        </span>
        <div>
          <h2
            id="result-heading"
            tabIndex={-1}
            className="text-2xl font-bold leading-tight outline-none sm:text-3xl"
            style={{ color: band.color }}
          >
            {headline.title}
          </h2>
          <p className="mt-1 text-lg">{headline.sub}</p>
        </div>
      </header>

      <div className="space-y-5 p-5 sm:p-6">
        {steps.length > 0 && (
          <section aria-labelledby="steps-title">
            <h3 id="steps-title" className="mb-3 text-lg font-bold">
              What to do
            </h3>
            <ul className="space-y-2.5">
              {steps.map((step, index) => (
                <li
                  key={index}
                  className="flex items-start gap-3 rounded-2xl border border-line-strong/40 bg-paper/60 px-4 py-3 text-lg"
                >
                  <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-jade text-on-jade">
                    <Check aria-hidden size={16} strokeWidth={3} />
                  </span>
                  {step}
                </li>
              ))}
            </ul>
          </section>
        )}

        {urgent && (
          <div
            role="note"
            className="rounded-2xl border-l-8 border-danger bg-[color-mix(in_srgb,var(--risk-critical)_12%,var(--card))] px-4 py-3 text-lg"
          >
            <strong>Already sent money or a code?</strong> Call your bank now, then call{" "}
            <strong className="text-2xl">997</strong>.
          </div>
        )}

        <details className="group rounded-2xl border border-line-strong/50">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 text-lg font-semibold [&::-webkit-details-marker]:hidden">
            Show details
            <span
              aria-hidden
              className="size-2.5 rotate-45 border-b-2 border-r-2 border-ink-2 transition-transform group-open:-rotate-[135deg]"
            />
          </summary>

          <div className="space-y-5 px-4 pb-5 pt-2">
            <Scale score={assessment.risk_score} active={band.key} />
            <p className="text-ink-2">
              Score {assessment.risk_score ?? "–"} out of 100 · Confidence {assessment.confidence}%
            </p>

            {assessment.assessment && <p className="text-lg">{assessment.assessment}</p>}

            {segments.length > 0 && (
              <section>
                <h3 className="mb-2 font-bold">The message, with warning signs marked</h3>
                <p className="whitespace-pre-wrap break-words rounded-2xl border border-line-strong/40 bg-paper/60 p-4 font-mono text-[0.95rem] leading-8">
                  {segments.map((segment, index) =>
                    segment.mark ? (
                      <mark
                        key={index}
                        className="rounded-sm border-b-2 border-warn bg-[color-mix(in_srgb,var(--risk-moderate)_30%,transparent)] px-0.5 text-ink"
                      >
                        {segment.text}
                        <sup className="ml-0.5 font-sans text-[0.7rem] font-extrabold">
                          {segment.mark}
                        </sup>
                      </mark>
                    ) : (
                      <span key={index}>{segment.text}</span>
                    ),
                  )}
                </p>
              </section>
            )}

            {indicators.length > 0 && (
              <section>
                <h3 className="mb-2 font-bold">Why we think so</h3>
                <ol className="space-y-3">
                  {indicators.map((item, index) => (
                    <li key={index} className="flex gap-3">
                      <span
                        className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full border-2 border-warn text-sm font-extrabold"
                        aria-hidden
                      >
                        {marked.has(index + 1) ? index + 1 : "•"}
                      </span>
                      <div className="min-w-0">
                        <strong
                          className={
                            item.type
                              ? "font-semibold capitalize"
                              : "break-all font-mono text-[0.95rem] font-semibold"
                          }
                        >
                          {(item.type ?? item.indicator ?? "signal").replace(/_/g, " ")}
                          {item.verdict ? ` · ${item.verdict}` : ""}
                        </strong>
                        {item.reason && <p>{item.reason}</p>}
                        {item.evidence && !marked.has(index + 1) && (
                          <p className="break-words font-mono text-sm text-ink-2">{item.evidence}</p>
                        )}
                        {item.report_link && (
                          <a
                            href={item.report_link}
                            target="_blank"
                            rel="noreferrer"
                            className="text-jade-text underline underline-offset-4"
                          >
                            Open full report (opens a new tab)
                          </a>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            )}

            <p className="text-sm text-ink-2">
              This is an estimate, not a final answer. Always confirm through an official number or
              website that you look up yourself.
            </p>
          </div>
        </details>
      </div>
    </article>
  );
}
