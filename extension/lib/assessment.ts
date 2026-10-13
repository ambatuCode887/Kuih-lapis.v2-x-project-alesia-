export type RiskLevel =
  | 'low'
  | 'moderate'
  | 'high'
  | 'critical'
  | 'insufficient_information';

/** One finding. Message analysis and URL checks use slightly different fields. */
export interface Indicator {
  type?: string;
  indicator?: string;
  verdict?: string;
  evidence?: string;
  reason?: string;
  report_link?: string;
}

/** The structured JSON produced by message_agent and url_check_agent. */
export interface Assessment {
  risk_score: number | null;
  risk_level: RiskLevel;
  confidence: number;
  indicators?: Indicator[];
  assessment?: string;
  recommended_actions?: string[];
  limitations?: string[];
}

const FENCED_JSON = /```(?:json)?\s*(\{[\s\S]*?\})\s*```/gi;

function asAssessment(value: unknown): Assessment | null {
  if (
    value &&
    typeof value === 'object' &&
    'confidence' in value &&
    'risk_level' in value
  ) {
    return value as Assessment;
  }
  return null;
}

/** Pull the assessment JSON out of an agent's text, fenced or bare. */
export function parseAssessment(text: string): Assessment | null {
  const fenced = [...text.matchAll(FENCED_JSON)].reverse();
  for (const match of fenced) {
    try {
      const found = asAssessment(JSON.parse(match[1] ?? ''));
      if (found) return found;
    } catch {
      // try the next block
    }
  }

  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start >= 0 && end > start) {
    try {
      return asAssessment(JSON.parse(text.slice(start, end + 1)));
    } catch {
      return null;
    }
  }
  return null;
}

export type BandKey = 'low' | 'moderate' | 'high' | 'critical' | 'unknown';

export interface RiskBand {
  key: BandKey;
  label: string;
  /** CSS variable holding the colour for this band. */
  color: string;
}

export function riskBand(level: RiskLevel, score: number | null): RiskBand {
  if (score === null || level === 'insufficient_information') {
    return { key: 'unknown', label: 'Unclear', color: 'var(--risk-unknown)' };
  }
  if (score >= 75) return { key: 'critical', label: 'Critical', color: 'var(--risk-critical)' };
  if (score >= 50) return { key: 'high', label: 'High', color: 'var(--risk-high)' };
  if (score >= 25) return { key: 'moderate', label: 'Moderate', color: 'var(--risk-moderate)' };
  return { key: 'low', label: 'Low', color: 'var(--risk-low)' };
}

export interface Segment {
  text: string;
  /** 1-based finding number when this stretch is highlighted. */
  mark?: number;
}

/**
 * Split the original text into plain and highlighted stretches, using each
 * finding's quoted evidence. Findings whose quote isn't found are skipped.
 */
export function highlightSegments(text: string, indicators: Indicator[]): Segment[] {
  const lower = text.toLowerCase();
  const ranges: { start: number; end: number; mark: number }[] = [];

  indicators.forEach((item, index) => {
    const quote = item.evidence?.trim();
    if (!quote || quote.length < 3) return;
    const start = lower.indexOf(quote.toLowerCase());
    if (start < 0) return;
    ranges.push({ start, end: start + quote.length, mark: index + 1 });
  });

  ranges.sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (range.start < cursor) continue; // overlaps an earlier highlight
    if (range.start > cursor) segments.push({ text: text.slice(cursor, range.start) });
    segments.push({ text: text.slice(range.start, range.end), mark: range.mark });
    cursor = range.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}
