import type { Assessment, Indicator } from "./assessment";

/**
 * Demo answers, used while no backend address is configured (NEXT_PUBLIC_API_URL).
 * They look for a few warning words so the page can be shown without a server.
 * They are NOT a real analysis, and the page says so.
 */

interface SampleRule {
  type: string;
  words: string[];
  reason: string;
  action?: string;
}

const RULES: SampleRule[] = [
  {
    type: "urgency",
    words: ["urgent", "immediately", "act now", "within 24", "expire", "suspended", "locked", "last warning"],
    reason: "Pressure to act quickly is a common way scammers stop people thinking.",
  },
  {
    type: "credential_request",
    words: ["otp", "password", "pin ", "tac ", "verify your", "confirm your"],
    reason: "Real banks and services never ask for codes or passwords by message.",
    action: "Do not share any code or password, even if the sender seems official.",
  },
  {
    type: "payment_request",
    words: ["transfer", "payment", "pay ", "bank in", "processing fee", "deposit"],
    reason: "Unexpected requests for money are a major warning sign.",
    action: "Do not send money until you have confirmed the request another way.",
  },
  {
    type: "suspicious_link",
    words: ["http://", "https://", "www.", "bit.ly"],
    reason: "Links in unexpected messages can lead to fake login pages.",
    action: "Do not open the link. Go to the official site by typing it yourself.",
  },
];

/** Quote the matched word plus the next few words, the way the real checker quotes evidence. */
function quoteAround(text: string, word: string): string | null {
  const index = text.toLowerCase().indexOf(word);
  if (index < 0) return null;
  const tail = text.slice(index).split(/\s+/).slice(0, 4).join(" ");
  return tail.replace(/[.,;:!?"')]+$/, "");
}

function sampleMessage(body: string): Assessment {
  const indicators: Indicator[] = [];
  const actions: string[] = [];
  for (const rule of RULES) {
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
      risk_level: "low",
      confidence: 55,
      indicators: [],
      assessment: "Demo result: no obvious scam wording found. That does not prove it is safe.",
      recommended_actions: ["If anything feels off, confirm with the sender another way."],
    };
  }

  const score = Math.min(95, 20 + indicators.length * 24);
  return {
    risk_score: score,
    risk_level: score >= 75 ? "critical" : score >= 50 ? "high" : "moderate",
    confidence: 70,
    indicators,
    assessment: `Demo result: ${indicators.length} warning sign${indicators.length > 1 ? "s" : ""} found in this message.`,
    recommended_actions: [
      ...actions,
      "Contact the organisation using a number or site you look up yourself.",
    ],
  };
}

function sampleLink(link: string): Assessment {
  const suspicious = /login|verify|secure|update|bank|free|gift|bit\.ly|\.xyz|\.top|\.click/i.test(link);
  return {
    risk_score: suspicious ? 68 : 15,
    risk_level: suspicious ? "high" : "low",
    confidence: 60,
    indicators: [
      {
        indicator: link.replace(/^https?:\/\//i, "").split(/[/?#]/)[0] || link,
        verdict: suspicious ? "suspicious" : "clean",
        evidence: suspicious
          ? "The address contains words often used in fake sites (demo data)."
          : "No detections in the demo data.",
      },
    ],
    assessment: suspicious
      ? "Demo result: this address looks like the kind used in fake sites."
      : "Demo result: no detections, but that does not prove the link is safe.",
    recommended_actions: suspicious
      ? ["Do not open it. Go to the official website by typing the address yourself."]
      : ["Check the address carefully before entering any details."],
  };
}

export interface SampleReply {
  text: string;
  assessment: Assessment | null;
}

export async function sampleReply(
  kind: "message" | "link" | "question",
  body: string,
  hasImages: boolean,
): Promise<SampleReply> {
  await new Promise((resolve) => setTimeout(resolve, 900));
  const note = "**Demo mode.** This site is not connected to the checker yet, so this is example data.";

  if (hasImages && !body.trim()) {
    return {
      text: `${note} I cannot read screenshots in demo mode, so this is an example result.`,
      assessment: sampleMessage("URGENT: verify your OTP now"),
    };
  }
  if (kind === "link") return { text: note, assessment: sampleLink(body.trim()) };
  if (kind === "message") return { text: note, assessment: sampleMessage(body) };
  return {
    text:
      `${note}\n\nReal answers to security questions will appear here once the checker is connected.`,
    assessment: null,
  };
}
