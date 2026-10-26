"use client";

import {
  useEffect,
  useRef,
  useState,
  type ClipboardEvent,
  type DragEvent,
} from "react";
import type { LucideIcon } from "lucide-react";
import Markdown from "react-markdown";
import {
  ArrowRight,
  ImagePlus,
  Link2,
  MessageCircleQuestion,
  MessageSquareText,
  RotateCcw,
  TriangleAlert,
  X,
} from "lucide-react";
import {
  DEMO_MODE,
  askChecker,
  isAbortError,
  isLlmUnavailableError,
  resetSession,
  type CheckMode,
} from "@/lib/check/api";
import { MAX_IMAGES, isImageFile, prepareImage } from "@/lib/check/images";
import {
  clearHistory,
  loadHistory,
  saveHistory,
  type HistoryEntry,
} from "@/lib/check/history";
import { HistoryList } from "./history-list";
import { VerdictCard } from "./verdict-card";

interface ModeConfig {
  id: CheckMode;
  label: string;
  icon: LucideIcon;
  heading: string;
  placeholder: string;
  help: string;
}

const MODES: ModeConfig[] = [
  {
    id: "message",
    label: "A message",
    icon: MessageSquareText,
    heading: "Paste the message",
    placeholder: "Paste the text, email or chat message here",
    help: "Copy the whole message, then paste it in the box. You can also add a screenshot of it.",
  },
  {
    id: "link",
    label: "A link",
    icon: Link2,
    heading: "Paste the link",
    placeholder: "Paste the website address here",
    help: "Do not open the link first. We look it up for you.",
  },
  {
    id: "question",
    label: "A question",
    icon: MessageCircleQuestion,
    heading: "Ask your question",
    placeholder: "For example: How can I tell if a text from my bank is fake?",
    help: "Ask anything about staying safe from scams online.",
  },
];

// One-tap examples, so anyone can see how it works without a real scam message.
const EXAMPLES: { label: string; mode: CheckMode; text: string }[] = [
  {
    label: "Fake bank text",
    mode: "message",
    text: "URGENT: Your bank account is locked. Verify your OTP at http://bit.ly/secure-bank within 24 hours to avoid suspension.",
  },
  { label: "Suspicious link", mode: "link", text: "http://secure-bank-login.top/verify" },
  {
    label: "Safety question",
    mode: "question",
    text: "How can I tell if a text from my bank is fake?",
  },
];

interface Shown {
  entry: HistoryEntry;
  /** Screenshots just sent. Not saved, so only present for a check done in this visit. */
  images: string[];
  earlier: boolean;
}

type Phase = "idle" | "checking" | "done" | "error";

export function Checker() {
  const [mode, setMode] = useState<CheckMode>("message");
  const [text, setText] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [llmUnavailable, setLlmUnavailable] = useState(false);
  const [notice, setNotice] = useState("");
  const [shown, setShown] = useState<Shown | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const noticeTimer = useRef<number | undefined>(undefined);

  // History lives in this browser. It can only be read after the page has loaded.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHistory(loadHistory());
    return () => window.clearTimeout(noticeTimer.current);
  }, []);

  const config = MODES.find((item) => item.id === mode) ?? MODES[0];
  const busy = phase === "checking";
  const canCheck = !busy && (text.trim().length > 0 || images.length > 0);

  function showNotice(message: string) {
    setNotice(message);
    window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(""), 5000);
  }

  async function addFiles(files: File[]) {
    const pictures = files.filter(isImageFile);
    if (pictures.length < files.length) showNotice("Only pictures can be added.");
    if (pictures.length === 0) return;

    const room = MAX_IMAGES - images.length;
    if (room <= 0 || pictures.length > room) {
      showNotice(`You can add up to ${MAX_IMAGES} pictures.`);
      if (room <= 0) return;
    }
    try {
      const prepared = await Promise.all(pictures.slice(0, room).map(prepareImage));
      setImages((current) => [...current, ...prepared].slice(0, MAX_IMAGES));
    } catch (cause) {
      showNotice(cause instanceof Error ? cause.message : "That picture could not be added.");
    }
  }

  function onPaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const files = [...event.clipboardData.items]
      .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
      .flatMap((item) => {
        const file = item.getAsFile();
        return file ? [file] : [];
      });
    if (files.length === 0) return; // a plain text paste carries on as normal
    event.preventDefault();
    void addFiles(files);
  }

  function onDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setDragging(false);
    void addFiles([...event.dataTransfer.files]);
  }

  function showResult(next: Shown) {
    setShown(next);
    setPhase("done");
  }

  // Once an answer has been drawn, move focus to it so screen readers announce it, and bring
  // it into view. Doing this after the render (not on a timer) means the heading always exists.
  useEffect(() => {
    if (phase !== "done" || !shown) return;
    document.getElementById("result-heading")?.focus({ preventScroll: true });
    resultRef.current?.scrollIntoView({ block: "start" });
  }, [phase, shown]);

  async function runCheck() {
    if (!canCheck) return;
    const sentText = text.trim();
    const sentImages = images;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setPhase("checking");
    setStatus("");
    setError("");
    setLlmUnavailable(false);
    setShown(null);

    try {
      const reply = await askChecker(mode, sentText, sentImages, {
        onStatus: setStatus,
        signal: controller.signal,
      });
      const entry: HistoryEntry = {
        id: crypto.randomUUID(),
        at: new Date().toISOString(),
        mode,
        title: (sentText || "Screenshot").replace(/\s+/g, " ").slice(0, 80),
        sourceText: reply.assessment && sentText ? sentText : undefined,
        assessment: reply.assessment,
        text: reply.text,
      };
      const next = [entry, ...history];
      setHistory(next);
      saveHistory(next);
      showResult({ entry, images: sentImages, earlier: false });
    } catch (cause) {
      if (isAbortError(cause)) {
        setPhase("idle");
        return;
      }
      if (isLlmUnavailableError(cause)) {
        setLlmUnavailable(true);
        setPhase("error");
        return;
      }
      setError(cause instanceof Error ? cause.message : "Something went wrong. Please try again.");
      setPhase("error");
    }
  }

  function stopCheck() {
    abortRef.current?.abort();
  }

  function startOver() {
    abortRef.current?.abort();
    resetSession();
    setText("");
    setImages([]);
    setShown(null);
    setError("");
    setPhase("idle");
    window.scrollTo({ top: 0 });
  }

  function openEntry(id: string) {
    const entry = history.find((item) => item.id === id);
    if (!entry) return;
    setMode(entry.mode);
    showResult({ entry, images: [], earlier: true });
  }

  function applyExample(example: (typeof EXAMPLES)[number]) {
    setMode(example.mode);
    setText(example.text);
    setImages([]);
  }

  // On a phone this is one column. It must be minmax(0,1fr): a plain grid column grows to fit
  // its widest content, so one long unbroken line would push every card past the screen edge.
  return (
    <>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-8 lg:grid-cols-[minmax(0,1fr)_21rem]">
      <div className="min-w-0 space-y-6">
        {DEMO_MODE && (
          <p
            role="note"
            className="rounded-2xl border-2 border-warn bg-[color-mix(in_srgb,var(--risk-moderate)_12%,var(--card))] px-4 py-3 text-lg"
          >
            <strong>Demo mode.</strong> This page is not connected to the checker yet, so the
            answers are examples.
          </p>
        )}

        <form
          onSubmit={(event) => {
            event.preventDefault();
            void runCheck();
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className={`glass space-y-5 rounded-3xl p-5 sm:p-7 ${
            dragging ? "outline-dashed outline-4 outline-jade" : ""
          }`}
        >
          <fieldset>
            <legend className="mb-3 text-lg font-bold">What do you want to check?</legend>
            <div className="grid grid-cols-3 gap-2 sm:gap-3">
              {MODES.map((item) => {
                const selected = item.id === mode;
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => setMode(item.id)}
                    className={`flex min-h-20 flex-col items-center justify-center gap-1.5 rounded-2xl border-2 px-2 py-3 text-center text-base font-bold transition-colors sm:text-lg ${
                      selected
                        ? "border-jade bg-jade text-on-jade"
                        : "border-line-strong bg-paper/60 hover:border-jade"
                    }`}
                  >
                    <Icon aria-hidden size={26} />
                    {item.label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div>
            <label htmlFor="check-input" className="mb-1 block text-lg font-bold">
              {config.heading}
            </label>
            <p id="check-help" className="mb-3 text-ink-2">
              {config.help}
            </p>
            <textarea
              id="check-input"
              value={text}
              onChange={(event) => setText(event.target.value)}
              onPaste={onPaste}
              onKeyDown={(event) => {
                if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                  event.preventDefault();
                  void runCheck();
                }
              }}
              rows={mode === "link" ? 2 : 6}
              placeholder={config.placeholder}
              aria-describedby="check-help"
              className="w-full resize-y rounded-2xl border-2 border-line-strong bg-card/80 p-4 text-lg leading-relaxed placeholder:text-ink-2 focus:border-jade"
            />
          </div>

          {images.length > 0 && (
            <ul aria-label="Pictures ready to check" className="flex flex-wrap gap-3">
              {images.map((src, index) => (
                <li key={index} className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={src}
                    alt={`Picture ${index + 1} ready to check`}
                    className="size-24 rounded-2xl border-2 border-line-strong object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => setImages((current) => current.filter((_, i) => i !== index))}
                    aria-label={`Remove picture ${index + 1}`}
                    className="absolute -right-2 -top-2 grid size-8 place-items-center rounded-full bg-danger text-paper ring-2 ring-card"
                  >
                    <X aria-hidden size={16} strokeWidth={3} />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {notice && (
            <p role="status" className="rounded-xl border-l-8 border-warn bg-paper/60 px-4 py-2">
              {notice}
            </p>
          )}

          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                multiple
                hidden
                onChange={(event) => {
                  void addFiles([...(event.target.files ?? [])]);
                  event.target.value = "";
                }}
              />
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="flex min-h-14 w-full items-center justify-center gap-2.5 rounded-full border-2 border-line-strong px-6 text-lg font-bold transition-colors hover:border-jade sm:w-auto"
              >
                <ImagePlus aria-hidden size={22} />
                Add a screenshot
              </button>
            </div>

            {busy ? (
              <button
                type="button"
                onClick={stopCheck}
                className="flex min-h-14 items-center justify-center gap-2.5 rounded-full border-2 border-line-strong px-8 text-lg font-bold"
              >
                Stop
              </button>
            ) : (
              <button
                type="submit"
                disabled={!canCheck}
                className="jade-gradient flex min-h-14 items-center justify-center gap-2.5 rounded-full px-10 text-xl font-bold text-on-jade shadow-lg transition-[filter,transform] enabled:hover:brightness-110 enabled:active:scale-[0.98] disabled:opacity-45"
              >
                Check
                <ArrowRight aria-hidden size={22} />
              </button>
            )}
          </div>

          <div className="border-t border-line-strong/40 pt-4">
            <p className="mb-2 text-ink-2">Want to see how it works? Try an example:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <button
                  key={example.label}
                  type="button"
                  onClick={() => applyExample(example)}
                  className="min-h-11 rounded-full border-2 border-line-strong px-4 font-semibold transition-colors hover:border-jade hover:text-jade-text"
                >
                  {example.label}
                </button>
              ))}
            </div>
          </div>
        </form>

        {phase !== "idle" && (
          <p role="note" className="ai-note -mt-2 text-center text-sm text-ink-2">
            Project Alesia can make mistakes. Check important info.
          </p>
        )}

        <div ref={resultRef} aria-live="polite" aria-busy={busy} className="scroll-mt-24 space-y-5">
          {busy && (
            <div role="status" className="space-y-3">
              <div aria-hidden className="glass animate-pulse space-y-4 rounded-3xl p-6">
                <div className="flex items-center gap-4">
                  <span className="size-16 rounded-full bg-line" />
                  <span className="flex-1 space-y-3">
                    <span className="block h-6 w-3/4 rounded-lg bg-line" />
                    <span className="block h-4 w-1/2 rounded-lg bg-line" />
                  </span>
                </div>
                <span className="block h-12 rounded-2xl bg-line" />
                <span className="block h-12 w-4/5 rounded-2xl bg-line" />
              </div>
              <p className="text-lg text-ink-2">{status || "Checking… this can take a minute."}</p>
            </div>
          )}

          {phase === "error" && !llmUnavailable && (
            <div role="alert" className="glass flex gap-4 rounded-3xl border-l-8 border-l-danger p-5 sm:p-6">
              <TriangleAlert aria-hidden size={30} className="mt-0.5 shrink-0 text-danger" />
              <div>
                <h2 id="result-heading" tabIndex={-1} className="text-xl font-bold outline-none">
                  We could not check that
                </h2>
                <p className="mt-1 text-lg">{error}</p>
                <button
                  type="button"
                  onClick={() => void runCheck()}
                  className="mt-4 min-h-12 rounded-full border-2 border-jade px-6 text-lg font-bold text-jade-text hover:bg-jade hover:text-on-jade"
                >
                  Try again
                </button>
              </div>
            </div>
          )}

          {phase === "done" && shown && (
            <>
              {shown.earlier && (
                <p
                  role="status"
                  className="rounded-2xl border-l-8 border-jade bg-card/70 px-4 py-3 text-lg font-semibold"
                >
                  You are looking at an earlier check.
                </p>
              )}

              {shown.images.length > 0 && (
                <ul aria-label="Pictures you sent" className="flex flex-wrap gap-3">
                  {shown.images.map((src, index) => (
                    // eslint-disable-next-line @next/next/no-img-element
                    <li key={index}><img src={src} alt={`Picture ${index + 1} you sent`} className="size-24 rounded-2xl border-2 border-line-strong object-cover" /></li>
                  ))}
                </ul>
              )}

              {shown.entry.assessment ? (
                <>
                  <VerdictCard
                    assessment={shown.entry.assessment}
                    sourceText={shown.entry.sourceText}
                  />
                  {shown.entry.text && (
                    <div className="glass space-y-3 rounded-3xl p-5 text-lg sm:p-6 [&_a]:text-jade-text [&_a]:underline [&_li]:ml-5 [&_li]:list-disc">
                      <Markdown>{shown.entry.text}</Markdown>
                    </div>
                  )}
                </>
              ) : (
                <article className="glass rounded-3xl p-5 sm:p-7">
                  <h2 id="result-heading" tabIndex={-1} className="mb-3 text-2xl font-bold outline-none">
                    Here is what we found
                  </h2>
                  <div className="space-y-3 text-lg leading-relaxed [&_a]:text-jade-text [&_a]:underline [&_li]:ml-5 [&_li]:list-disc">
                    <Markdown>{shown.entry.text}</Markdown>
                  </div>
                </article>
              )}

              <button
                type="button"
                onClick={startOver}
                className="flex min-h-14 items-center gap-2.5 rounded-full border-2 border-line-strong px-6 text-lg font-bold transition-colors hover:border-jade"
              >
                <RotateCcw aria-hidden size={20} />
                Check something else
              </button>
            </>
          )}
        </div>
      </div>

      <aside aria-label="Your recent checks" className="min-w-0 lg:sticky lg:top-24 lg:self-start">
        <HistoryList
          entries={history}
          activeId={shown?.earlier ? shown.entry.id : null}
          onOpen={openEntry}
          onClear={() => {
            clearHistory();
            setHistory([]);
            if (shown?.earlier) {
              setShown(null);
              setPhase("idle");
            }
          }}
        />
      </aside>
    </div>
      {llmUnavailable && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 p-4"
          role="presentation"
        >
          <section
            aria-labelledby="llm-outage-title"
            aria-modal="true"
            className="w-full max-w-md rounded-3xl border border-line bg-card p-6 shadow-2xl sm:p-8"
            role="alertdialog"
          >
            <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-danger/10 text-danger">
              <TriangleAlert aria-hidden size={26} />
            </div>
            <h2 className="text-2xl font-bold" id="llm-outage-title">
              Our AI is temporarily unavailable
            </h2>
            <p className="mt-3 text-lg text-ink-2">
              Gemini and the backup AI could not respond. Please try again in a few minutes.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                autoFocus
                className="min-h-12 rounded-full bg-jade px-6 text-lg font-bold text-on-jade hover:opacity-90"
                onClick={() => void runCheck()}
                type="button"
              >
                Try again
              </button>
              <button
                className="min-h-12 rounded-full border-2 border-line px-6 text-lg font-bold hover:bg-paper"
                onClick={() => setLlmUnavailable(false)}
                type="button"
              >
                Close
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
