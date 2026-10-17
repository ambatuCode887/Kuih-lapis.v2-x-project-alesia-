/** VirusTotal detection counts for the domain checked in this reply. */
export interface DomainStats {
  malicious: number;
  suspicious: number;
}

interface ToolResponsePart {
  functionResponse?: {
    name?: string;
    response?: {
      structuredContent?: unknown;
      content?: { type?: string; text?: string }[];
    };
  };
}

function statsFrom(report: unknown): DomainStats | null {
  const stats = (report as { data?: { last_analysis_stats?: Record<string, unknown> } } | null)
    ?.data?.last_analysis_stats;
  if (typeof stats?.malicious !== 'number' || typeof stats?.suspicious !== 'number') {
    return null;
  }
  return { malicious: stats.malicious, suspicious: stats.suspicious };
}

function statsFromText(content: { text?: string }[] | undefined): DomainStats | null {
  const text = content?.[0]?.text;
  if (!text) return null;
  try {
    return statsFrom(JSON.parse(text));
  } catch {
    return null;
  }
}

interface DomainStatsMetadata {
  kind?: string;
  malicious?: unknown;
  suspicious?: unknown;
}

/**
 * Reads the counts for the domain checked in this reply. Prefers the backend's
 * deterministic `domain_stats` event, then falls back to the get_domain_report
 * tool result in the agent's event stream.
 */
export function extractDomainStats(
  events: ReadonlyArray<{
    content?: { parts?: ToolResponsePart[] };
    customMetadata?: DomainStatsMetadata;
  }>,
): DomainStats | null {
  let stats: DomainStats | null = null;
  for (const event of events) {
    const meta = event.customMetadata;
    if (meta?.kind === 'domain_stats' && typeof meta.malicious === 'number' && typeof meta.suspicious === 'number') {
      stats = { malicious: meta.malicious, suspicious: meta.suspicious };
    }
  }
  if (stats) return stats;
  for (const event of events) {
    for (const part of event.content?.parts ?? []) {
      const call = part.functionResponse;
      if (call?.name !== 'get_domain_report') continue;
      stats =
        statsFrom(call.response?.structuredContent) ??
        statsFromText(call.response?.content) ??
        stats;
    }
  }
  return stats;
}

/** Clean only when VirusTotal reports no malicious and no suspicious detections. */
export function isCleanDomain(stats: DomainStats | null | undefined): boolean {
  return stats != null && stats.malicious === 0 && stats.suspicious === 0;
}
