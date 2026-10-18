import { useEffect, useState } from 'react';
import {
  highlightSegments,
  riskBand,
  type Assessment,
  type BandKey,
} from '@/lib/assessment';
import { AlertIcon, QuestionIcon, ShieldCheckIcon, SpeakerIcon } from './Icons';

const SCALE: { key: BandKey; label: string }[] = [
  { key: 'low', label: 'Low' },
  { key: 'moderate', label: 'Medium' },
  { key: 'high', label: 'High' },
  { key: 'critical', label: 'Very high' },
];

// Plain-language headline for each risk band. It never promises that
// something is safe: a clean result only means no warning signs were found.
const HEADLINES: Record<BandKey, { title: string; sub: string }> = {
  critical: {
    title: 'This looks like a scam',
    sub: 'Do not reply, click or send anything.',
  },
  high: {
    title: 'This looks like a scam',
    sub: 'Do not reply, click or send anything.',
  },
  moderate: {
    title: 'Be careful',
    sub: 'Some things look suspicious.',
  },
  low: {
    title: 'No warning signs found',
    sub: 'If you are unsure, check with the sender another way.',
  },
  unknown: {
    title: 'Not sure',
    sub: "There isn't enough to tell. Check with someone you trust.",
  },
};

const MAX_STEPS = 3;

interface VerdictSlipProps {
  assessment: Assessment;
  /** What the user sent, shown back with the suspicious parts marked. */
  sourceText?: string;
}

function VerdictIcon({ band }: { band: BandKey }) {
  if (band === 'low') return <ShieldCheckIcon width={44} height={44} />;
  if (band === 'unknown') return <QuestionIcon width={44} height={44} />;
  return <AlertIcon width={44} height={44} />;
}

function Scale({ score, active }: { score: number | null; active: BandKey }) {
  return (
    <div
      className="scale"
      role="img"
      aria-label={`Level of concern: ${SCALE.find((band) => band.key === active)?.label.toLowerCase() ?? 'not known'}`}
    >
      <div className="scale-bar">
        {SCALE.map((band) => (
          <span
            key={band.key}
            className={`scale-seg scale-${band.key}${band.key === active ? ' is-active' : ''}`}
          />
        ))}
        {score !== null && (
          <span className="scale-pin" style={{ left: `${Math.min(100, Math.max(0, score))}%` }} />
        )}
      </div>
      <div className="scale-labels">
        {SCALE.map((band) => (
          <span key={band.key}>{band.label}</span>
        ))}
      </div>
    </div>
  );
}

export default function VerdictSlip({ assessment, sourceText }: VerdictSlipProps) {
  const band = riskBand(assessment.risk_level, assessment.risk_score);
  const headline = HEADLINES[band.key];
  const indicators = assessment.indicators ?? [];
  const steps = (assessment.recommended_actions ?? []).slice(0, MAX_STEPS);
  const segments = sourceText ? highlightSegments(sourceText, indicators) : [];
  const markedNumbers = new Set(segments.flatMap((s) => (s.mark ? [s.mark] : [])));
  const urgent = (assessment.risk_score ?? 0) >= 50;
  const [speaking, setSpeaking] = useState(false);

  // Stop talking if the card goes away.
  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  function toggleSpeech() {
    const synth = window.speechSynthesis;
    if (!synth) return;
    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      return;
    }
    const spoken = [
      headline.title + '.',
      headline.sub,
      steps.length ? 'What to do. ' + steps.join(' ') : '',
    ].join(' ');
    const utterance = new SpeechSynthesisUtterance(spoken);
    utterance.rate = 0.9;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    synth.cancel();
    synth.speak(utterance);
    setSpeaking(true);
  }

  return (
    <article className={`slip slip-${band.key}`} style={{ ['--band' as string]: band.color }}>
      <header className="verdict" role="status">
        <span className="verdict-icon">
          <VerdictIcon band={band.key} />
        </span>
        <div className="verdict-text">
          <h2 className="verdict-title">{headline.title}</h2>
          <p className="verdict-sub">{headline.sub}</p>
        </div>
      </header>

      {steps.length > 0 && (
        <section className="steps">
          <h3 className="steps-title">What to do</h3>
          <ul className="todo">
            {steps.map((step, index) => (
              <li key={index}>{step}</li>
            ))}
          </ul>
        </section>
      )}

      {urgent && (
        <div className="urgent" role="note">
          <strong>Already sent money or a code?</strong> Call your bank now, then call{' '}
          <strong className="urgent-number">997</strong>.
        </div>
      )}

      <button
        type="button"
        className={`read-aloud${speaking ? ' is-on' : ''}`}
        onClick={toggleSpeech}
        aria-pressed={speaking}
      >
        <SpeakerIcon width={22} height={22} />
        {speaking ? 'Stop reading' : 'Read aloud'}
      </button>

      <details className="details">
        <summary>Show details</summary>

        <div className="details-body">
          <Scale score={assessment.risk_score} active={band.key} />
          <p className="details-score">
            How worried to be: {assessment.risk_score ?? '–'} out of 100 · How sure we are: {assessment.confidence}%
          </p>

          {assessment.assessment && <p className="slip-summary">{assessment.assessment}</p>}

          {segments.length > 0 && (
            <section className="slip-section">
              <h3 className="slip-label">The message, with warning signs marked</h3>
              <p className="received">
                {segments.map((segment, index) =>
                  segment.mark ? (
                    <mark key={index} className="hl" style={{ ['--i' as string]: segment.mark }}>
                      {segment.text}
                      <sup>{segment.mark}</sup>
                    </mark>
                  ) : (
                    <span key={index}>{segment.text}</span>
                  ),
                )}
              </p>
            </section>
          )}

          {indicators.length > 0 && (
            <section className="slip-section">
              <h3 className="slip-label">Why we think so</h3>
              <ol className="findings">
                {indicators.map((item, index) => (
                  <li key={index} className="finding">
                    <span className="finding-no">{markedNumbers.has(index + 1) ? index + 1 : '•'}</span>
                    <div>
                      <strong className={`finding-type${item.type ? '' : ' mono'}`}>
                        {(item.type ?? item.indicator ?? 'signal').replace(/_/g, ' ')}
                        {item.verdict ? ` · ${item.verdict}` : ''}
                      </strong>
                      {item.reason && <p>{item.reason}</p>}
                      {item.evidence && !markedNumbers.has(index + 1) && (
                        <p className="finding-evidence">{item.evidence}</p>
                      )}
                      {item.report_link && (
                        <a href={item.report_link} target="_blank" rel="noreferrer">
                          Open full report (opens a new tab)
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <p className="slip-foot">
            This is an estimate, not a final answer. Always confirm through an official number or
            website that you look up yourself.
          </p>
        </div>
      </details>
    </article>
  );
}
