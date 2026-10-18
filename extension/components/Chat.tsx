import {
  useEffect,
  useRef,
  useState,
  type ClipboardEvent,
  type ComponentType,
  type DragEvent,
  type SVGProps,
} from "react";
import Markdown from "react-markdown";
import "@fontsource-variable/plus-jakarta-sans";
import "@fontsource/ibm-plex-mono/400.css";
import { askAgent, isAbortError, resetSession } from "@/lib/api";
import { parseAssessment, riskBand, type Assessment } from "@/lib/assessment";
import { MAX_IMAGES, isImageFile, prepareImage } from "@/lib/images";
import { useTheme } from "@/lib/theme";
import AppearanceMenu from "./AppearanceMenu";
import DownloadWarning from "./DownloadWarning";
import {
  CloseIcon,
  ArrowIcon,
  ChevronsLeftIcon,
  ExpandIcon,
  LinkIcon,
  Mark,
  MessageIcon,
  PaperclipIcon,
  PencilIcon,
  TrashIcon,
  PlusIcon,
  QuestionIcon,
  SendIcon,
  ShieldCheckIcon,
  StopIcon,
} from "./Icons";
import Lightbox from "./Lightbox";
import ShieldScan from "./ShieldScan";
import VerdictSlip from "./VerdictSlip";
import "./tailwind.css";
import "./chat.css";
import "./attachments.css";
import "./polish.css";
import "./friendly.css";
import "./visuals.css";
import "./web-look.css";

export interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  /** Screenshots the user sent, as data URLs. */
  images?: string[];
  /** Present when a message or link was risk-assessed. */
  assessment?: Assessment;
  /** What the user asked us to check, shown back with findings marked. */
  sourceText?: string;
  /** ADK event authors that participated in this response. */
  agents?: string[];
  /** Cached questions shown as one-tap follow-ups. */
  relatedQuestions?: string[];
  isError?: boolean;
  /** A name the user gave this check in the sidebar (user messages only). */
  title?: string;
}

const STORAGE_KEY = "chat-messages";
// "New check" does not delete anything. It remembers the last message that was on screen,
// and only messages after it are shown. The full log stays, so Recent checks keeps its history.
const VIEW_AFTER_KEY = "chat-view-after";
// Keep the saved log from growing forever (screenshots are large).
const MAX_SAVED_MESSAGES = 200;
// Written by the right-click menu in background.ts; consumed here.
const PENDING_KEY = "pending-check";

function normalizeMessages(messages: Message[]): Message[] {
  return messages.map((message) => ({
    ...message,
    assessment: message.assessment
      ? (parseAssessment(JSON.stringify(message.assessment)) ?? undefined)
      : undefined,
  }));
}

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

interface QuickAction {
  icon: Icon;
  title: string;
  description: string;
  /** Text placed in the input box; the user finishes it and sends. */
  prompt: string;
  /** Colour the card turns to on hover. */
  tint: string;
}

// Prompts are worded so the backend's router picks the right specialist.
const QUICK_ACTIONS: QuickAction[] = [
  {
    icon: MessageIcon,
    title: "Check a message",
    description: "A text, email or chat",
    prompt: 'Analyze this message: "',
    tint: "var(--pine)",
  },
  {
    icon: LinkIcon,
    title: "Check a link",
    description: "A website address",
    prompt: "Check this link: ",
    tint: "var(--teal)",
  },
  {
    icon: QuestionIcon,
    title: "Ask a question",
    description: "About staying safe online",
    prompt: "How can I protect myself from phishing?",
    tint: "var(--risk-moderate)",
  },
];

/** Strip the routing wrapper so only the user's own content is shown back. */
function extractSource(prompt: string): string | undefined {
  const message = prompt.match(
    /^analy[sz]e this message:\s*"?([\s\S]*?)"?\s*$/i,
  );
  if (message?.[1]) return message[1].trim();
  const link = prompt.match(/^check this link:\s*(\S[\s\S]*)$/i);
  return link?.[1]?.trim();
}

interface ChatProps {
  /** Side panel: compact, with an Expand button. Tab: wide, with a history rail. */
  layout?: "panel" | "tab";
  /** Opens the full-tab version. */
  onExpand?: () => void;
}

export default function Chat({ layout = "panel", onExpand }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  // The history sidebar can be minimised to a thin strip. The choice is remembered.
  const [railMin, setRailMin] = useState(() => {
    try {
      const saved = localStorage.getItem(layout === "panel" ? "rail-minimised-panel" : "rail-minimised");
      if (saved === null) return layout === "panel";
      return saved === "1";
    } catch {
      return false;
    }
  });
  function toggleRail() {
    setRailMin((current) => {
      const next = !current;
      try {
        localStorage.setItem(layout === "panel" ? "rail-minimised-panel" : "rail-minimised", next ? "1" : "0");
      } catch {
        /* remembering the choice is optional */
      }
      return next;
    });
  }
  const [attachments, setAttachments] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [status, setStatus] = useState("");
  const [loaded, setLoaded] = useState(false);
  // id of the last message hidden by "New check"; null means show everything.
  const [viewAfter, setViewAfter] = useState<string | null>(null);
  // Renaming and deleting single checks in the sidebar.
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const renameSkip = useRef(false);
  // id of an earlier check opened from Recent checks, shown on its own.
  const [focusId, setFocusId] = useState<string | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const { theme, chooseTheme } = useTheme();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [dragging, setDragging] = useState(false);
  const dragDepth = useRef(0);
  const fileRef = useRef<HTMLInputElement>(null);
  const loadingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const sendTextRef = useRef(sendText);
  sendTextRef.current = sendText;

  // Load saved history, and keep both views (panel and tab) in sync.
  useEffect(() => {
    browser.storage.local.get([STORAGE_KEY, VIEW_AFTER_KEY]).then((result) => {
      const savedView = result[VIEW_AFTER_KEY];
      if (typeof savedView === "string") setViewAfter(savedView);
      const saved = result[STORAGE_KEY] as Message[] | undefined;
      // Drop the old welcome bubble that earlier versions saved.
      const history = saved?.filter((message) => message.id !== "welcome");
      if (history?.length) setMessages(normalizeMessages(history));
      setLoaded(true);
    });

    const onChange = (
      changes: Record<string, { newValue?: unknown }>,
      area: string,
    ) => {
      if (area === "local" && changes[STORAGE_KEY]?.newValue) {
        setMessages(
          normalizeMessages(changes[STORAGE_KEY].newValue as Message[]),
        );
      }
      if (area === "local" && VIEW_AFTER_KEY in changes) {
        const next = changes[VIEW_AFTER_KEY]?.newValue;
        setViewAfter(typeof next === "string" ? next : null);
      }
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, []);

  useEffect(() => {
    if (loaded) {
      browser.storage.local
        .set({ [STORAGE_KEY]: messages.slice(-MAX_SAVED_MESSAGES) })
        .catch(() => {
          showNotice("Chat history could not be saved.");
        });
    }
  }, [messages, loaded]);

  // Handle "Check with Project Alesia" from the right-click menu.
  useEffect(() => {
    if (!loaded) return;

    async function consumePending() {
      const result = await browser.storage.local.get(PENDING_KEY);
      const pending = result[PENDING_KEY] as { prompt?: string } | undefined;
      if (!pending?.prompt) return;
      // Remove first so the other open view doesn't run it too.
      await browser.storage.local.remove(PENDING_KEY);
      sendTextRef.current(pending.prompt);
    }

    consumePending();
    const onChange = (changes: Record<string, unknown>, area: string) => {
      if (area === "local" && PENDING_KEY in changes) consumePending();
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, [loaded]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendText(rawText: string, images: string[] = []) {
    const text = rawText.trim();
    if ((!text && images.length === 0) || loadingRef.current) return;

    loadingRef.current = true;
    setFocusId(null);
    setLoading(true);
    setStatus("");
    const controller = new AbortController();
    abortRef.current = controller;
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        text,
        images: images.length ? images : undefined,
      },
    ]);

    const assistantId = crypto.randomUUID();
    let participatingAgents: string[] = [];

    function rememberAgent(author: string) {
      if (participatingAgents.includes(author)) return;
      participatingAgents = [...participatingAgents, author];
      setActiveAgents([...participatingAgents]);
    }

    try {
      const reply = await askAgent(
        text,
        images,
        setStatus,
        rememberAgent,
        controller.signal,
      );
      const finalMessage: Message = {
        id: assistantId,
        role: "assistant",
        text: reply.text,
        assessment: reply.assessment ?? undefined,
        sourceText: reply.assessment && text ? extractSource(text) : undefined,
        agents: reply.agents?.length ? reply.agents : participatingAgents,
        relatedQuestions: reply.relatedQuestions?.length
          ? reply.relatedQuestions
          : undefined,
      };
      setMessages((current) => [...current, finalMessage]);
      setActiveAgents([]);
    } catch (error) {
      if (isAbortError(error)) {
        const stoppedMessage: Message = {
          id: assistantId,
          role: "assistant",
          text: "Stopped. No result was returned.",
          agents: participatingAgents,
        };
        setMessages((current) => [...current, stoppedMessage]);
      } else {
        const errorText =
          error instanceof Error ? error.message : "Something went wrong.";
        const errorMessage: Message = {
          id: assistantId,
          role: "assistant",
          text: errorText,
          agents: participatingAgents,
          isError: true,
        };
        setMessages((current) => [...current, errorMessage]);
      }
      setActiveAgents([]);
    } finally {
      abortRef.current = null;
      loadingRef.current = false;
      setLoading(false);
      setStatus("");
    }
  }

  function stopGeneration() {
    abortRef.current?.abort();
  }

  function send() {
    const text = input;
    const images = attachments;
    setInput("");
    setAttachments([]);
    sendText(text, images);
  }

  function showNotice(message: string) {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 4000);
  }

  async function addFiles(files: File[]) {
    const images = files.filter(isImageFile);
    if (images.length < files.length)
      showNotice("Only images can be attached.");
    if (images.length === 0) return;

    const room = MAX_IMAGES - attachments.length;
    if (room <= 0 || images.length > room) {
      showNotice(`You can attach up to ${MAX_IMAGES} images.`);
      if (room <= 0) return;
    }

    try {
      const prepared = await Promise.all(
        images.slice(0, room).map(prepareImage),
      );
      setAttachments((current) =>
        [...current, ...prepared].slice(0, MAX_IMAGES),
      );
    } catch (error) {
      showNotice(
        error instanceof Error ? error.message : "Could not add that image.",
      );
    }
  }

  function onPaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    const files = [...event.clipboardData.items]
      .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
      .flatMap((item) => {
        const file = item.getAsFile();
        return file ? [file] : [];
      });
    if (files.length === 0) return; // a plain text paste continues as normal
    event.preventDefault();
    addFiles(files);
  }

  function onDrop(event: DragEvent<HTMLFormElement>) {
    event.preventDefault();
    dragDepth.current = 0;
    setDragging(false);
    addFiles([...event.dataTransfer.files]);
  }

  // Count enter/leave pairs so moving over child elements doesn't flicker the drop zone.
  function onDragEnter(event: DragEvent<HTMLFormElement>) {
    if (![...event.dataTransfer.types].includes("Files")) return;
    dragDepth.current += 1;
    setDragging(true);
  }

  function onDragLeave() {
    dragDepth.current = Math.max(0, dragDepth.current - 1);
    if (dragDepth.current === 0) setDragging(false);
  }

  function newCheck() {
    // A check that is still running belongs to the old session, so stop it first.
    abortRef.current?.abort();
    // Start a fresh screen but keep the saved log, so Recent checks is not lost.
    const lastId = messages.at(-1)?.id ?? null;
    setViewAfter(lastId);
    if (lastId) browser.storage.local.set({ [VIEW_AFTER_KEY]: lastId });
    setFocusId(null);
    setInput("");
    setAttachments([]);
    // Forget the backend session: the next prompt opens a brand-new one with no memory
    // of the earlier conversation.
    void resetSession();
    inputRef.current?.focus();
  }

  /** The only way to delete history: a deliberate, confirmed action. */
  function clearHistory() {
    setMessages([]);
    setViewAfter(null);
    setFocusId(null);
    setConfirmClear(false);
    browser.storage.local.remove(VIEW_AFTER_KEY);
    resetSession();
  }

  function startRename(id: string, current: string) {
    renameSkip.current = false;
    setConfirmDeleteId(null);
    setRenameDraft(current);
    setRenamingId(id);
  }

  /** Save the new name. An empty name goes back to the automatic one. */
  function commitRename() {
    if (renameSkip.current) {
      renameSkip.current = false;
      return;
    }
    const id = renamingId;
    if (!id) return;
    const name = renameDraft.trim().slice(0, 80);
    setMessages((current) =>
      current.map((message) => (message.id === id ? { ...message, title: name || undefined } : message)),
    );
    setRenamingId(null);
  }

  /** Remove one check (the question and its answer). The other checks are untouched. */
  function deleteCheck(id: string) {
    const index = messages.findIndex((message) => message.id === id);
    if (index === -1) return;
    if (loading && index >= messages.length - 2) {
      showNotice("Stop the running check first, then delete it.");
      setConfirmDeleteId(null);
      return;
    }
    const removed = new Set([id]);
    const reply = messages[index + 1];
    if (reply?.role === "assistant") removed.add(reply.id);

    // If the screen was cut off at one of the removed messages, cut it off just before them.
    if (viewAfter && removed.has(viewAfter)) {
      const before = messages.slice(0, index).at(-1)?.id ?? null;
      setViewAfter(before);
      if (before) browser.storage.local.set({ [VIEW_AFTER_KEY]: before });
      else browser.storage.local.remove(VIEW_AFTER_KEY);
    }
    if (focusId && removed.has(focusId)) setFocusId(null);
    setMessages((current) => current.filter((message) => !removed.has(message.id)));
    setConfirmDeleteId(null);
  }

  function openPastCheck(id: string) {
    const onScreen = visible.some((message) => message.id === id);
    if (onScreen && !focusId) {
      document.getElementById(`msg-${id}`)?.scrollIntoView({ behavior: "smooth" });
    } else {
      setFocusId(id);
    }
  }

  function applyQuickAction(action: QuickAction) {
    setInput(action.prompt);
    const field = inputRef.current;
    if (field) {
      field.focus();
      // Put the cursor at the end so the user can keep typing.
      requestAnimationFrame(() =>
        field.setSelectionRange(action.prompt.length, action.prompt.length),
      );
    }
  }

  // The message box grows with its text, up to a limit, then scrolls.
  useEffect(() => {
    const field = inputRef.current;
    if (!field) return;
    field.style.height = "auto";
    field.style.height = `${Math.min(field.scrollHeight, 220)}px`;
  }, [input]);

  // What is on screen: one earlier check on its own, or the messages since "New check".
  const visible = (() => {
    if (focusId) {
      const start = messages.findIndex((message) => message.id === focusId);
      if (start >= 0) {
        const reply = messages[start + 1];
        return reply?.role === "assistant"
          ? [messages[start]!, reply]
          : [messages[start]!];
      }
    }
    if (viewAfter) {
      const hidden = messages.findIndex((message) => message.id === viewAfter);
      if (hidden >= 0) return messages.slice(hidden + 1);
    }
    return messages;
  })();

  const isEmpty = visible.length === 0;

  // Recent checks for the sidebar: one entry per question the user sent, whether or not
  // the reply came with a risk score. (Only scored replies used to be listed, so plain
  // security questions never appeared.)
  const history = messages.flatMap((message, index) => {
    if (message.role !== "user") return [];
    const reply = messages[index + 1];
    const assessment = reply?.role === "assistant" ? reply.assessment : undefined;
    const typed = message.text.trim();
    const title =
      (typed && extractSource(typed)) ||
      typed ||
      (message.images?.length ? "Screenshot" : "Check");
    return [
      {
        id: message.id,
        score: assessment ? assessment.risk_score : null,
        band: assessment
          ? riskBand(assessment.risk_level, assessment.risk_score)
          : null,
        title: message.title?.trim() || title,
      },
    ];
  });

  return (
    <div className={`app app-${layout}`}>
      <div className="glass-bg" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <DownloadWarning />
      {(layout === "tab" || layout === "panel") && (
        <aside className={`rail${railMin ? " rail--min" : ""}`} aria-label="Recent checks">
          <div className="rail-head">
            <div className="brand">
              <Mark />
              <span className="brand-name">Project Alesia</span>
            </div>
            <button
              type="button"
              className="ghost icon-only rail-toggle"
              onClick={toggleRail}
              aria-expanded={!railMin}
              aria-controls="rail-body"
              aria-label={railMin ? "Show recent checks" : "Minimise recent checks"}
              title={railMin ? "Show recent checks" : "Minimise"}
            >
              <ChevronsLeftIcon width={20} height={20} className="rail-chevron" />
            </button>
          </div>
          <button type="button" className="rail-new" onClick={newCheck} aria-label="New check" title="New check">
            <PlusIcon width={16} height={16} /> <span className="rail-new-text">New check</span>
          </button>
          <div id="rail-body" className="rail-body" inert={railMin}>
          <div className="rail-body-inner">
          <h2 className="rail-title">Recent checks</h2>
          {history.length === 0 ? (
            <p className="rail-empty">Checks you run appear here.</p>
          ) : (
            <ul className="rail-list">
              {[...history].reverse().map((item) => (
                <li key={item.id} className="rail-row">
                  {renamingId === item.id ? (
                    <input
                      className="rail-rename"
                      value={renameDraft}
                      maxLength={80}
                      autoFocus
                      aria-label="Rename this check"
                      onChange={(event) => setRenameDraft(event.target.value)}
                      onFocus={(event) => event.target.select()}
                      onBlur={commitRename}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          commitRename();
                        } else if (event.key === "Escape") {
                          renameSkip.current = true;
                          setRenamingId(null);
                        }
                      }}
                    />
                  ) : confirmDeleteId === item.id ? (
                    <div className="rail-confirm-row" role="group" aria-label="Confirm delete">
                      <span>Delete this check?</span>
                      <button type="button" className="rail-danger" onClick={() => deleteCheck(item.id)}>
                        Delete
                      </button>
                      <button type="button" className="ghost" onClick={() => setConfirmDeleteId(null)}>
                        Keep
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="rail-item"
                        aria-current={focusId === item.id ? "true" : undefined}
                        onClick={() => openPastCheck(item.id)}
                      >
                        {item.band ? (
                          <span className={`chip chip-${item.band.key}`}>
                            {item.score ?? "–"}
                          </span>
                        ) : (
                          <span className="chip chip-question" title="Question">
                            Q
                          </span>
                        )}
                        <span className="rail-item-text">{item.title}</span>
                      </button>
                      <div className="rail-actions">
                        <button
                          type="button"
                          className="rail-act"
                          aria-label={`Rename ${item.title}`}
                          title="Rename"
                          onClick={() => startRename(item.id, item.title)}
                        >
                          <PencilIcon width={16} height={16} />
                        </button>
                        <button
                          type="button"
                          className="rail-act"
                          aria-label={`Delete ${item.title}`}
                          title="Delete"
                          onClick={() => {
                            setRenamingId(null);
                            setConfirmDeleteId(item.id);
                          }}
                        >
                          <TrashIcon width={16} height={16} />
                        </button>
                      </div>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
          {history.length > 0 &&
            (confirmClear ? (
              <div className="rail-confirm" role="group" aria-label="Confirm clearing history">
                <p>Delete all recent checks?</p>
                <button type="button" className="rail-danger" onClick={clearHistory}>
                  Yes, delete
                </button>
                <button type="button" className="ghost" onClick={() => setConfirmClear(false)}>
                  Keep them
                </button>
              </div>
            ) : (
              <button type="button" className="rail-clear" onClick={() => setConfirmClear(true)}>
                Clear history
              </button>
            ))}
          </div>
          </div>
          <div className="appearance-dock">
            <AppearanceMenu theme={theme} onChange={chooseTheme} />
          </div>
        </aside>
      )}

      <div className="chat">
        {layout === "panel" && (
          <header className="bar">
            <div className="brand">
              <Mark />
              <span className="brand-name">Project Alesia</span>
            </div>
            <div className="bar-actions">
              {onExpand && (
                <button
                  type="button"
                  className="ghost icon-only"
                  onClick={onExpand}
                  aria-label="Open in a full tab"
                  title="Open in a full tab"
                >
                  <ExpandIcon width={16} height={16} />
                </button>
              )}
            </div>
          </header>
        )}

        <div className="scroll">
          <div className="thread">
            {isEmpty && !loading && (
              <section className="welcome">
                <div className="welcome-hero">
                  <h1 className="welcome-title">
                    Got something suspicious?
                  </h1>
                  <p className="welcome-lead">
                    Paste a message, link or screenshot. I&apos;ll tell you if it looks like a scam.
                  </p>
                </div>
              </section>
            )}

            {focusId && (
              <div className="viewing" role="status">
                <span>You are looking at an earlier check.</span>
                <button type="button" className="ghost" onClick={() => setFocusId(null)}>
                  Back to current chat
                </button>
              </div>
            )}

            {visible.map((message) => (
              <div key={message.id} id={`msg-${message.id}`} className="turn">
                {message.assessment && (
                  <VerdictSlip
                    assessment={message.assessment}
                    sourceText={message.sourceText}
                  />
                )}
                {message.role === "user" ? (
                  <>
                    {message.images && message.images.length > 0 && (
                      <div className="sent-images">
                        {message.images.map((src, index) => (
                          <button
                            key={index}
                            type="button"
                            className="sent-image"
                            onClick={() => setPreview(src)}
                            aria-label="View image full size"
                          >
                            <img
                              src={src}
                              alt={`Screenshot ${index + 1} you sent`}
                            />
                          </button>
                        ))}
                      </div>
                    )}
                    {message.text && <div className="said">{message.text}</div>}
                  </>
                ) : message.isError ? (
                  <div className="reply reply-error">{message.text}</div>
                ) : message.assessment ? (
                  <details className="reply-more">
                    <summary>Read the full explanation</summary>
                    <div className="reply">
                      <Markdown>{message.text}</Markdown>
                    </div>
                  </details>
                ) : (
                  <div className="reply">
                    <Markdown>{message.text}</Markdown>
                  </div>
                )}
                {message.role === "assistant" &&
                  !!message.relatedQuestions?.length && (
                    <div
                      className="related-questions"
                      aria-label="Related questions"
                    >
                      <span className="related-questions-label">
                        Related questions
                      </span>
                      {message.relatedQuestions.map((question) => (
                        <button
                          key={question}
                          type="button"
                          className="related-question"
                          disabled={loading}
                          onClick={() => sendText(question)}
                        >
                          {question}
                        </button>
                      ))}
                    </div>
                  )}
                {message.role === "assistant" && !!message.agents?.length && (
                  <div
                    className="agent-trace"
                    aria-label="Agents that participated"
                  >
                    <span className="agent-trace-label">Agents</span>
                    <span className="agent-trace-names">
                      {message.agents.join(" → ")}
                    </span>
                  </div>
                )}
              </div>
            ))}

            {loading && activeAgents.length > 0 && (
              <div
                className="agent-trace"
                aria-label="Agents working on this response"
              >
                <span className="agent-trace-label">Agents</span>
                <span className="agent-trace-names">
                  {activeAgents.join(" → ")}
                </span>
              </div>
            )}

            {loading && (
              <div className="working" role="status">
                <ShieldScan />
                {status || "Analyzing context…"}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {notice && (
          <p className="notice" role="status">
            {notice}
          </p>
        )}

        {isEmpty && !loading && (
          <ul className="quick-lines" aria-label="Start a check">
            {QUICK_ACTIONS.map((action) => (
              <li key={action.title}>
                <button
                  type="button"
                  className="quick-line hover-tint"
                  style={{ ["--tint" as string]: action.tint }}
                  onClick={() => applyQuickAction(action)}
                >
                  <span className="quick-line-icon">
                    <action.icon width={20} height={20} />
                  </span>
                  <span className="quick-line-title">{action.title}</span>
                  <span className="quick-line-text">{action.description}</span>
                  <ArrowIcon width={16} height={16} className="quick-line-arrow" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <form
          className={`composer${dragging ? " is-dragging" : ""}`}
          onSubmit={(event) => {
            event.preventDefault();
            send();
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          {dragging && (
            <div className="drop-zone" aria-hidden="true">
              <PaperclipIcon width={26} height={26} />
              <span>Drop your screenshot here</span>
            </div>
          )}
          {attachments.length > 0 && (
            <ul className="attachments" aria-label="Images ready to send">
              {attachments.map((src, index) => (
                <li key={index} className="attachment">
                  <button
                    type="button"
                    className="attachment-thumb"
                    onClick={() => setPreview(src)}
                    aria-label={`Preview image ${index + 1}`}
                  >
                    <img src={src} alt={`Image ${index + 1} ready to send`} />
                  </button>
                  <button
                    type="button"
                    className="attachment-remove"
                    onClick={() =>
                      setAttachments((current) =>
                        current.filter((_, i) => i !== index),
                      )
                    }
                    aria-label={`Remove image ${index + 1}`}
                  >
                    <CloseIcon width={12} height={12} />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="composer-row">
            <button
              type="button"
              className="attach"
              onClick={() => fileRef.current?.click()}
              aria-label="Add a photo"
              title="Add a photo or screenshot"
            >
              <PaperclipIcon width={22} height={22} />
              <span>Photo</span>
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(event) => {
                addFiles([...(event.target.files ?? [])]);
                event.target.value = "";
              }}
            />
            <textarea
              ref={inputRef}
              value={input}
              placeholder="Paste a message, link or screenshot…"
              rows={1}
              aria-label="Message"
              onChange={(event) => setInput(event.target.value)}
              onPaste={onPaste}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  send();
                }
              }}
            />
            {loading ? (
              <button
                type="button"
                className="send is-stop"
                onClick={stopGeneration}
                aria-label="Stop"
                title="Stop this check"
              >
                <StopIcon width={22} height={22} />
                <span>Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                className="send"
                disabled={!input.trim() && attachments.length === 0}
                aria-label="Check"
              >
                <SendIcon width={22} height={22} />
                <span>Check</span>
              </button>
            )}
          </div>
        </form>
        {(!isEmpty || loading) && (
          <p className="ai-note" role="note">
            Project Alesia can make mistakes. Check important info.
          </p>
        )}
      </div>
      {preview && <Lightbox src={preview} onClose={() => setPreview(null)} />}
    </div>
  );
}
