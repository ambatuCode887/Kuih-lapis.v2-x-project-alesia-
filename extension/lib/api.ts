import { parseAssessment, type Assessment, type Indicator } from './assessment';
import { extractDomainStats, type DomainStats } from './domainStats';
import { splitDataUrl } from './images';

/**
 * Set to true to talk to the real ADK server (`adk api_server`).
 * While false, the extension answers with built-in sample replies.
 */
const USE_BACKEND = true;

const DEFAULT_BACKEND_URL = 'https://kuih-lapis-v2-x-project-alesia.onrender.com';
const APP_NAME = 'agents';
const USER_ID = 'extension-user';
const SESSION_KEY = 'session-id';
const BACKEND_KEY = 'backend-url';
const LLM_FAILOVER_MARKER = 'LLM_FAILOVER_EXHAUSTED';

// Agents whose output is the structured risk assessment.
const ASSESSMENT_AUTHORS = new Set(['message_agent', 'url_check_agent']);

export interface AgentReply {
  /** The final, user-facing answer. */
  text: string;
  assessment: Assessment | null;
  /** ADK event authors observed during this response, in first-seen order. */
  agents?: string[];
  /** Cached questions the user can send for an instant answer. */
  relatedQuestions?: string[];
  /** VirusTotal counts from get_domain_report, or null when no domain was checked. */
  domainStats?: DomainStats | null;
}

interface AdkPart {
  text?: string;
  functionResponse?: {
    name?: string;
    response?: {
      structuredContent?: unknown;
      content?: { type?: string; text?: string }[];
    };
  };
}

interface AdkEvent {
  author?: string;
  content?: { parts?: AdkPart[] };
  turnComplete?: boolean;
  customMetadata?: {
    status?: string;
    kind?: string;
    questions?: string[];
    assessment?: unknown;
  };
}

async function backendUrl(): Promise<string> {
  const stored = await browser.storage.local.get(BACKEND_KEY);
  const url = (stored[BACKEND_KEY] as string | undefined) ?? DEFAULT_BACKEND_URL;
  return url.replace(/\/+$/, '');
}

function eventText(event: AdkEvent): string {
  return (event.content?.parts ?? [])
    .map((part) => part.text ?? '')
    .join('')
    .trim();
}

export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError';
}

export function isLlmUnavailableError(error: unknown): boolean {
  return error instanceof Error && error.message === LLM_FAILOVER_MARKER;
}

async function readAgentEvents(
  response: Response,
  onStatus?: (status: string) => void,
  onAgent?: (author: string) => void,
): Promise<AdkEvent[]> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('The backend did not return a response stream.');

  const decoder = new TextDecoder();
  const events: AdkEvent[] = [];
  let buffer = '';

  const consumeFrame = (frame: string) => {
    const data = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n');
    if (!data) return;

    const payload = JSON.parse(data) as AdkEvent & {
      error?: string;
      error_details?: { error_message?: string };
    };
    if (payload.error) {
      const message = payload.error_details?.error_message ?? payload.error;
      throw new Error(message.includes(LLM_FAILOVER_MARKER) ? LLM_FAILOVER_MARKER : message);
    }

    const event = payload as AdkEvent;
    events.push(event);
    if (event.author) onAgent?.(event.author);
    const status = event.customMetadata?.status;
    if (status) onStatus?.(status);
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? '';
      for (const frame of frames) consumeFrame(frame);
      if (done) break;
    }
    if (buffer.trim()) consumeFrame(buffer);
  } finally {
    reader.releaseLock();
  }

  return events;
}

async function ensureSession(base: string): Promise<string> {
  const stored = await browser.storage.local.get(SESSION_KEY);
  const existing = stored[SESSION_KEY] as string | undefined;
  const sessions = `${base}/apps/${APP_NAME}/users/${USER_ID}/sessions`;

  if (existing) {
    const check = await fetch(`${sessions}/${existing}`);
    if (check.ok) return existing;
  }

  const sessionId = existing ?? crypto.randomUUID();
  const created = await fetch(sessions, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId }),
  });
  if (!created.ok) {
    throw new Error(`Could not start a session (HTTP ${created.status}).`);
  }
  await browser.storage.local.set({ [SESSION_KEY]: sessionId });
  return sessionId;
}

/** Return the active conversation ID, creating a local ID before the first request. */
export async function getSessionId(): Promise<string> {
  const stored = await browser.storage.local.get(SESSION_KEY);
  const existing = stored[SESSION_KEY] as string | undefined;
  if (existing) return existing;
  const sessionId = crypto.randomUUID();
  await browser.storage.local.set({ [SESSION_KEY]: sessionId });
  return sessionId;
}

/** Start a new backend conversation boundary. The server session is created lazily. */
export async function startNewSession(sessionId: string = crypto.randomUUID()): Promise<string> {
  await browser.storage.local.set({ [SESSION_KEY]: sessionId });
  return sessionId;
}

/** Switch the backend conversation to an existing session from the sidebar. */
export async function switchSession(sessionId: string): Promise<string> {
  return startNewSession(sessionId);
}

/** Forget the session so the next message starts a fresh conversation. */
export async function resetSession(): Promise<void> {
  await browser.storage.local.remove(SESSION_KEY);
}

interface SampleRule {
  type: string;
  words: string[];
  reason: string;
  action?: string;
}

// Keyword rules used to fake an analysis while the backend is off.
const SAMPLE_RULES: SampleRule[] = [
  {
    type: 'urgency',
    words: ['urgent', 'immediately', 'act now', 'within 24', 'expire', 'suspended', 'locked', 'last warning'],
    reason: 'Pressure to act quickly is a common way scammers stop people thinking.',
  },
  {
    type: 'credential_request',
    words: ['otp', 'password', 'pin ', 'tac ', 'verify your', 'confirm your'],
    reason: 'Real banks and services never ask for codes or passwords by message.',
    action: 'Do not share any code or password, even if the sender seems official.',
  },
  {
    type: 'payment_request',
    words: ['transfer', 'payment', 'pay ', 'bank in', 'processing fee', 'deposit'],
    reason: 'Unexpected requests for money are a major warning sign.',
    action: 'Do not send money until you have confirmed the request another way.',
  },
  {
    type: 'suspicious_link',
    words: ['http://', 'https://', 'www.', 'bit.ly'],
    reason: 'Links in unexpected messages can lead to fake login pages.',
    action: 'Do not open the link. Go to the official site by typing it yourself.',
  },
];

/** Quote the matched word plus the next few words, as an agent would. */
function quoteAround(text: string, word: string): string | null {
  const index = text.toLowerCase().indexOf(word);
  if (index < 0) return null;
  const tail = text.slice(index).split(/\s+/).slice(0, 4).join(' ');
  return tail.replace(/[.,;:!?"')]+$/, '');
}

function sampleMessageRisk(body: string): Assessment {
  const indicators: Indicator[] = [];
  const actions: string[] = [];
  for (const rule of SAMPLE_RULES) {
    for (const word of rule.words) {
      const evidence = quoteAround(body, word);
      if (!evidence) continue;
      indicators.push({ type: rule.type, evidence, reason: rule.reason });
      if (rule.action) actions.push(rule.action);
      break;
    }
  }

  if (indicators.length === 0) {
    return {
      risk_score: 12,
      risk_level: 'low',
      confidence: 55,
      indicators: [],
      assessment: 'Sample result: no obvious scam wording found. That does not prove it is safe.',
      recommended_actions: ['If anything feels off, confirm with the sender another way.'],
    };
  }

  const score = Math.min(95, 20 + indicators.length * 24);
  return {
    risk_score: score,
    risk_level: score >= 75 ? 'critical' : score >= 50 ? 'high' : 'moderate',
    confidence: 70,
    indicators,
    assessment: `Sample result: ${indicators.length} warning sign${indicators.length > 1 ? 's' : ''} found in this message.`,
    recommended_actions: [
      ...actions,
      'Contact the organisation using a number or site you look up yourself.',
    ],
  };
}

const SAMPLE_LINK_RISK: Assessment = {
  risk_score: 18,
  risk_level: 'low',
  confidence: 64,
  indicators: [
    {
      indicator: 'example.com',
      verdict: 'clean',
      evidence: '0 malicious, 0 suspicious detections (sample data)',
    },
  ],
  assessment: 'Sample result: no detections, but that does not prove the link is safe.',
  recommended_actions: ['Check the address carefully before entering any details.'],
};

/** Offline stand-in used while USE_BACKEND is false. */
async function sampleReply(message: string, images: string[]): Promise<AgentReply> {
  await new Promise((resolve) => setTimeout(resolve, 700));
  const lower = message.toLowerCase();

  if (images.length > 0) {
    return {
      text:
        '**Sample reply.** The backend is turned off, so I could not read your screenshot. ' +
        'This is an example result.',
      assessment: sampleMessageRisk('URGENT: verify your OTP now'),
    };
  }

  if (lower.startsWith('check this link') || /https?:\/\/|www\./.test(lower)) {
    return {
      text: '**Sample reply.** The backend is turned off, so this is demo data.',
      assessment: SAMPLE_LINK_RISK,
    };
  }
  if (lower.includes('analyze this message') || lower.includes('analyse this message')) {
    const body = message.replace(/^analy[sz]e this message:\s*"?/i, '').replace(/"\s*$/, '');
    return {
      text: '**Sample reply.** The backend is turned off, so this is demo data.',
      assessment: sampleMessageRisk(body),
    };
  }
  return {
    text:
      "**Sample reply.** The backend is turned off, so I can't answer real questions yet.\n\n" +
      '- Try **Check a message** or **Check a link** to preview the risk card.',
    assessment: null,
  };
}

export async function askAgent(
  message: string,
  images: string[] = [],
  onStatus?: (status: string) => void,
  onAgent?: (author: string) => void,
  signal?: AbortSignal,
): Promise<AgentReply> {
  if (!USE_BACKEND) return sampleReply(message, images);

  const base = await backendUrl();
  let response: Response;
  try {
    const sessionId = await ensureSession(base);
    response = await fetch(`${base}/run_sse`, {
      method: 'POST',
      signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        appName: APP_NAME,
        userId: USER_ID,
        sessionId,
        streaming: false,
        newMessage: {
          role: 'user',
          parts: [
            { text: message || 'Analyze this screenshot.' },
            ...images.map((image, index) => {
              const { mimeType, data } = splitDataUrl(image);
              return {
                inlineData: {
                  mimeType,
                  data,
                  displayName: `screenshot-${index + 1}.jpg`,
                },
              };
            }),
          ],
        },
      }),
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new Error(
      `Can't reach the backend at ${base}. Is "adk api_server" running?`,
    );
  }
  if (!response.ok) {
    const details = await response.text().catch(() => '');
    if (details.includes(LLM_FAILOVER_MARKER)) {
      throw new Error(LLM_FAILOVER_MARKER);
    }
    throw new Error(`The backend returned an error (HTTP ${response.status}).`);
  }

  const events = await readAgentEvents(response, onStatus, onAgent);

  let assessment: Assessment | null = null;
  for (const event of events) {
    if (event.author && ASSESSMENT_AUTHORS.has(event.author)) {
      const metadataAssessment = event.customMetadata?.assessment;
      const metadataText =
        metadataAssessment && typeof metadataAssessment === 'object'
          ? JSON.stringify(metadataAssessment)
          : undefined;
      assessment =
        parseAssessment(eventText(event)) ??
        (metadataText ? parseAssessment(metadataText) : null) ??
        assessment;
    }
  }
  if (
    !assessment &&
    events.some(
      (event) => event.author && ASSESSMENT_AUTHORS.has(event.author),
    )
  ) {
    assessment = {
      risk_score: null,
      risk_level: 'insufficient_information',
      confidence: 0,
      indicators: [],
      assessment:
        'The specialist responded without a readable structured assessment. Treat the result as unverified.',
      recommended_actions: [
        'Verify the link or message through the service’s official channel before acting.',
      ],
    };
  }

  // The root agent writes the final answer, and retrieval-only replies are
  // the retrieval agent's passages.
  const answers = events.filter(
    (event) =>
      (event.author === 'root_agent' || event.author === 'retrieval_agent') &&
      eventText(event),
  );
  const relatedQuestions = events
    .filter((event) => event.customMetadata?.kind === 'related_questions')
    .flatMap((event) => event.customMetadata?.questions ?? []);
  const lastAnswer = answers.at(-1);
  const text = lastAnswer
    ? eventText(lastAnswer)
    : 'The assistant did not return an answer.';
  const agents = [
    ...new Set(
      events
        .map((event) => event.author)
        .filter((author): author is string => Boolean(author)),
    ),
  ];

  const domainStats = extractDomainStats(events);
  return { text, assessment, agents, relatedQuestions, domainStats };
}
