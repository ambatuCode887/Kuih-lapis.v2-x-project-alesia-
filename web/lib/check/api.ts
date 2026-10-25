import { parseAssessment, type Assessment } from "./assessment";
import { splitDataUrl } from "./images";
import { sampleReply } from "./sample";

/**
 * Talks to the ADK backend (`adk api_server`), the same one the Chrome extension uses.
 *
 * Set NEXT_PUBLIC_API_URL (for example in web/.env.local) to the backend's address.
 * With no address, the page runs in demo mode with example answers.
 */
const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
export const DEMO_MODE = API_URL === "";

const APP_NAME = "agents";
const USER_ID = "web-user";
const SESSION_KEY = "cyber-assistant-session";
const LLM_FAILOVER_MARKER = "LLM_FAILOVER_EXHAUSTED";

// Agents whose output is the structured risk assessment.
const ASSESSMENT_AUTHORS = new Set(["message_agent", "url_check_agent"]);

export type CheckMode = "message" | "link" | "question";

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
  customMetadata?: { status?: string };
}

/** The wording the backend's router recognises for each kind of check. */
export function buildPrompt(mode: CheckMode, text: string): string {
  const body = text.trim();
  if (!body) return "";
  if (mode === "link") return `Check this link: ${body}`;
  if (mode === "message") return `Analyze this message: "${body}"`;
  return body;
}

function eventText(event: AdkEvent): string {
  return (event.content?.parts ?? [])
    .map((part) => part.text ?? "")
    .join("")
    .trim();
}

export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

export function isLlmUnavailableError(error: unknown): boolean {
  return error instanceof Error && error.message === LLM_FAILOVER_MARKER;
}

async function readAgentEvents(
  response: Response,
  onStatus?: (status: string) => void,
): Promise<AdkEvent[]> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("The checker did not send an answer.");

  const decoder = new TextDecoder();
  const events: AdkEvent[] = [];
  let buffer = "";

  const consumeFrame = (frame: string) => {
    const data = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return;

    const payload = JSON.parse(data) as AdkEvent & {
      error?: string;
      error_details?: { error_message?: string };
    };
    if (payload.error) {
      const message = payload.error_details?.error_message ?? payload.error;
      throw new Error(message.includes(LLM_FAILOVER_MARKER) ? LLM_FAILOVER_MARKER : message);
    }
    events.push(payload);
    const status = payload.customMetadata?.status;
    if (status) onStatus?.(status);
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";
      for (const frame of frames) consumeFrame(frame);
      if (done) break;
    }
    if (buffer.trim()) consumeFrame(buffer);
  } finally {
    reader.releaseLock();
  }
  return events;
}

async function ensureSession(): Promise<string> {
  const sessions = `${API_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions`;
  const existing = window.sessionStorage.getItem(SESSION_KEY);

  if (existing) {
    const check = await fetch(`${sessions}/${existing}`);
    if (check.ok) return existing;
  }

  const sessionId = crypto.randomUUID();
  const created = await fetch(sessions, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId }),
  });
  if (!created.ok) {
    throw new Error(`Could not start a check (error ${created.status}).`);
  }
  window.sessionStorage.setItem(SESSION_KEY, sessionId);
  return sessionId;
}

/** Forget the conversation so the next check starts fresh. */
export function resetSession(): void {
  window.sessionStorage.removeItem(SESSION_KEY);
}

export async function askChecker(
  mode: CheckMode,
  text: string,
  images: string[],
  options: { onStatus?: (status: string) => void; signal?: AbortSignal } = {},
): Promise<AgentReply> {
  if (DEMO_MODE) return sampleReply(mode, text, images.length > 0);

  const message = buildPrompt(mode, text) || "Analyze this screenshot.";
  let response: Response;
  try {
    const sessionId = await ensureSession();
    response = await fetch(`${API_URL}/run_sse`, {
      method: "POST",
      signal: options.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        appName: APP_NAME,
        userId: USER_ID,
        sessionId,
        streaming: false,
        newMessage: {
          role: "user",
          parts: [
            { text: message },
            ...images.map((image, index) => {
              const { mimeType, data } = splitDataUrl(image);
              return {
                inlineData: { mimeType, data, displayName: `screenshot-${index + 1}.jpg` },
              };
            }),
          ],
        },
      }),
    });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new Error("We could not reach the checker. Please try again in a moment.");
  }
  if (!response.ok) {
    const details = await response.text().catch(() => "");
    if (details.includes(LLM_FAILOVER_MARKER)) {
      throw new Error(LLM_FAILOVER_MARKER);
    }
    throw new Error(`The checker had a problem (error ${response.status}). Please try again.`);
  }

  const events = await readAgentEvents(response, options.onStatus);

  let assessment: Assessment | null = null;
  for (const event of events) {
    if (event.author && ASSESSMENT_AUTHORS.has(event.author)) {
      assessment = parseAssessment(eventText(event)) ?? assessment;
    }
  }
  // A specialist answered but its result could not be read: say so, instead of guessing.
  if (
    !assessment &&
    events.some((event) => event.author && ASSESSMENT_AUTHORS.has(event.author))
  ) {
    assessment = {
      risk_score: null,
      risk_level: "insufficient_information",
      confidence: 0,
      indicators: [],
      assessment:
        "The checker answered, but its result could not be read. Treat this as unverified.",
      recommended_actions: [
        "Check the message or link through the organisation's official website or phone number.",
      ],
    };
  }

  // The root agent writes the final answer; knowledge questions come from the retrieval agent.
  const answers = events.filter(
    (event) =>
      (event.author === "root_agent" || event.author === "retrieval_agent") &&
      eventText(event),
  );
  const last = answers.at(-1);
  return {
    text: last ? eventText(last) : "The checker did not return an answer.",
    assessment,
  };
}
