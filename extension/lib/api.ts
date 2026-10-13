import { parseAssessment, type Assessment, type Indicator } from './assessment';
import { splitDataUrl } from './images';

/**
 * Set to true to talk to the real ADK server (`adk api_server`).
 * While false, the extension answers with built-in sample replies.
 */
const USE_BACKEND = false;

const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';
const APP_NAME = 'agents';
const USER_ID = 'extension-user';
const SESSION_KEY = 'session-id';
const BACKEND_KEY = 'backend-url';

// Agents whose output is the structured risk assessment.
const ASSESSMENT_AUTHORS = new Set(['message_agent', 'url_check_agent']);

export interface AgentReply {
  /** The final, user-facing answer. */
  text: string;
  assessment: Assessment | null;
}

interface AdkPart {
  text?: string;
}

interface AdkEvent {
  author?: string;
  content?: { parts?: AdkPart[] };
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

async function ensureSession(base: string): Promise<string> {
  const stored = await browser.storage.local.get(SESSION_KEY);
  const existing = stored[SESSION_KEY] as string | undefined;
  const sessions = `${base}/apps/${APP_NAME}/users/${USER_ID}/sessions`;

  if (existing) {
    const check = await fetch(`${sessions}/${existing}`);
    if (check.ok) return existing;
  }

  const sessionId = crypto.randomUUID();
  const created = await fetch(sessions, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!created.ok) {
    throw new Error(`Could not start a session (HTTP ${created.status}).`);
  }
  await browser.storage.local.set({ [SESSION_KEY]: sessionId });
  return sessionId;
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

export async function askAgent(message: string, images: string[] = []): Promise<AgentReply> {
  if (!USE_BACKEND) return sampleReply(message, images);

  const base = await backendUrl();
  let response: Response;
  try {
    const sessionId = await ensureSession(base);
    response = await fetch(`${base}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        app_name: APP_NAME,
        user_id: USER_ID,
        session_id: sessionId,
        new_message: {
          role: 'user',
          parts: [
            { text: message || 'Analyze this screenshot.' },
            ...images.map((image, index) => {
              const { mimeType, data } = splitDataUrl(image);
              return {
                inline_data: {
                  mime_type: mimeType,
                  data,
                  display_name: `screenshot-${index + 1}.jpg`,
                },
              };
            }),
          ],
        },
      }),
    });
  } catch {
    throw new Error(
      `Can't reach the backend at ${base}. Is "adk api_server" running?`,
    );
  }
  if (!response.ok) {
    throw new Error(`The backend returned an error (HTTP ${response.status}).`);
  }

  const events = (await response.json()) as AdkEvent[];

  let assessment: Assessment | null = null;
  for (const event of events) {
    if (event.author && ASSESSMENT_AUTHORS.has(event.author)) {
      assessment = parseAssessment(eventText(event)) ?? assessment;
    }
  }

  // The root agent writes the final answer, so take its last text event.
  const answers = events.filter(
    (event) => event.author === 'root_agent' && eventText(event),
  );
  const lastAnswer = answers.at(-1);
  const text = lastAnswer
    ? eventText(lastAnswer)
    : 'The assistant did not return an answer.';

  return { text, assessment };
}
