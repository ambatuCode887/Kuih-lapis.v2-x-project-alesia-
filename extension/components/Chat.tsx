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
import "@fontsource-variable/instrument-sans";
import "@fontsource/ibm-plex-mono/400.css";
import { askAgent, resetSession } from "@/lib/api";
import { riskBand, type Assessment } from "@/lib/assessment";
import { MAX_IMAGES, isImageFile, prepareImage } from "@/lib/images";
import { useTheme } from "@/lib/theme";
import {
  CloseIcon,
  ExpandIcon,
  LinkIcon,
  Mark,
  MessageIcon,
  MicIcon,
  MoonIcon,
  PaperclipIcon,
  PlusIcon,
  QuestionIcon,
  SendIcon,
  StopIcon,
  SunIcon,
} from "./Icons";
import Lightbox from "./Lightbox";
import VerdictSlip from "./VerdictSlip";
import "./chat.css";
import "./attachments.css";
import "./polish.css";
import "./friendly.css";

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
  isError?: boolean;
}

const STORAGE_KEY = "chat-messages";
// Written by the right-click menu in background.ts; consumed here.
const PENDING_KEY = "pending-check";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

interface QuickAction {
  icon: Icon;
  title: string;
  description: string;
  /** Text placed in the input box; the user finishes it and sends. */
  prompt: string;
}

// Prompts are worded so the backend's router picks the right specialist.
const QUICK_ACTIONS: QuickAction[] = [
  {
    icon: MessageIcon,
    title: "Check a message",
    description: "A text, email or chat",
    prompt: 'Analyze this message: "',
  },
  {
    icon: LinkIcon,
    title: "Check a link",
    description: "A website address",
    prompt: "Check this link: ",
  },
  {
    icon: QuestionIcon,
    title: "Ask a question",
    description: "About staying safe online",
    prompt: "How can I protect myself from phishing?",
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
  const [attachments, setAttachments] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const { theme, toggleTheme } = useTheme();
  // Design only: this just switches the listening look. Speech recognition is not wired up yet.
  const [listening, setListening] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const loadingRef = useRef(false);
  const sendTextRef = useRef(sendText);
  sendTextRef.current = sendText;

  // Load saved history, and keep both views (panel and tab) in sync.
  useEffect(() => {
    browser.storage.local.get(STORAGE_KEY).then((result) => {
      const saved = result[STORAGE_KEY] as Message[] | undefined;
      // Drop the old welcome bubble that earlier versions saved.
      const history = saved?.filter((message) => message.id !== "welcome");
      if (history?.length) setMessages(history);
      setLoaded(true);
    });

    const onChange = (
      changes: Record<string, { newValue?: unknown }>,
      area: string,
    ) => {
      if (area === "local" && changes[STORAGE_KEY]?.newValue) {
        setMessages(changes[STORAGE_KEY].newValue as Message[]);
      }
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, []);

  useEffect(() => {
    if (loaded) {
      browser.storage.local.set({ [STORAGE_KEY]: messages }).catch(() => {
        showNotice("Chat history could not be saved.");
      });
    }
  }, [messages, loaded]);

  // Handle "Check with Cyber Assistant" from the right-click menu.
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
    setLoading(true);
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
    let hasProgress = false;
    try {
      const reply = await askAgent(text, images, (progress) => {
        hasProgress = true;
        setMessages((current) => {
          const existing = current.some(
            (message) => message.id === assistantId,
          );
          const progressMessage: Message = {
            id: assistantId,
            role: "assistant",
            text: progress,
          };
          return existing
            ? current.map((message) =>
                message.id === assistantId ? progressMessage : message,
              )
            : [...current, progressMessage];
        });
      });
      const finalMessage: Message = {
        id: assistantId,
        role: "assistant",
        text: reply.text,
        assessment: reply.assessment ?? undefined,
        sourceText: reply.assessment && text ? extractSource(text) : undefined,
      };
      setMessages((current) => {
        if (hasProgress) {
          return current.map((message) =>
            message.id === assistantId ? finalMessage : message,
          );
        }
        return [...current, finalMessage];
      });
    } catch (error) {
      const errorText =
        error instanceof Error ? error.message : "Something went wrong.";
      const errorMessage: Message = {
        id: assistantId,
        role: "assistant",
        text: errorText,
        isError: true,
      };
      setMessages((current) => {
        if (hasProgress) {
          return current.map((message) =>
            message.id === assistantId ? errorMessage : message,
          );
        }
        return [...current, errorMessage];
      });
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
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
    addFiles([...event.dataTransfer.files]);
  }

  function newCheck() {
    setMessages([]);
    setAttachments([]);
    resetSession();
    inputRef.current?.focus();
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

  const isEmpty = messages.length === 0;

  // Past checks for the history rail: every assessed reply with its source.
  const history = messages.flatMap((message) =>
    message.assessment
      ? [
          {
            id: message.id,
            score: message.assessment.risk_score,
            band: riskBand(
              message.assessment.risk_level,
              message.assessment.risk_score,
            ),
            title: message.sourceText ?? "Check",
          },
        ]
      : [],
  );

  return (
    <div className={`app app-${layout}`}>
      {layout === "tab" && (
        <aside className="rail">
          <div className="rail-head">
            <div className="brand">
              <Mark />
              <span className="brand-name">Cyber Assistant</span>
            </div>
            <button
              type="button"
              className="ghost icon-only"
              onClick={toggleTheme}
              aria-label={
                theme === "dark"
                  ? "Switch to light mode"
                  : "Switch to dark mode"
              }
              title={theme === "dark" ? "Light mode" : "Dark mode"}
            >
              {theme === "dark" ? (
                <SunIcon width={20} height={20} />
              ) : (
                <MoonIcon width={20} height={20} />
              )}
            </button>
          </div>
          <button type="button" className="rail-new" onClick={newCheck}>
            <PlusIcon width={16} height={16} /> New check
          </button>
          <h2 className="rail-title">Recent checks</h2>
          {history.length === 0 ? (
            <p className="rail-empty">Checks you run appear here.</p>
          ) : (
            <ul className="rail-list">
              {[...history].reverse().map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="rail-item"
                    onClick={() =>
                      document
                        .getElementById(`msg-${item.id}`)
                        ?.scrollIntoView({ behavior: "smooth" })
                    }
                  >
                    <span className={`chip chip-${item.band.key}`}>
                      {item.score ?? "–"}
                    </span>
                    <span className="rail-item-text">{item.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
      )}

      <div className="chat">
        {layout === "panel" && (
          <header className="bar">
            <div className="brand">
              <Mark />
              <span className="brand-name">Cyber Assistant</span>
            </div>
            <div className="bar-actions">
              <button
                type="button"
                className="ghost icon-only"
                onClick={toggleTheme}
                aria-label={
                  theme === "dark"
                    ? "Switch to light mode"
                    : "Switch to dark mode"
                }
                title={theme === "dark" ? "Light mode" : "Dark mode"}
              >
                {theme === "dark" ? (
                  <SunIcon width={20} height={20} />
                ) : (
                  <MoonIcon width={20} height={20} />
                )}
              </button>
              <button
                type="button"
                className="ghost"
                onClick={newCheck}
                disabled={isEmpty}
              >
                New check
              </button>
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
                <h1 className="welcome-title">Got something suspicious?</h1>
                <p className="welcome-lead">
                  Paste it here. I'll tell you if it looks like a scam.
                </p>
                <ul className="starters">
                  {QUICK_ACTIONS.map((action) => (
                    <li key={action.title}>
                      <button
                        type="button"
                        className="starter"
                        onClick={() => applyQuickAction(action)}
                      >
                        <span className="starter-icon">
                          <action.icon />
                        </span>
                        <span className="starter-text">
                          <strong>{action.title}</strong>
                          <small>{action.description}</small>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
                <p className="welcome-tip">You can also paste a screenshot.</p>
              </section>
            )}

            {messages.map((message) => (
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
              </div>
            ))}

            {loading && (
              <div className="working" role="status">
                <span className="dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                Checking…
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

        <form
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            send();
          }}
          onDragOver={(event) => event.preventDefault()}
          onDrop={onDrop}
        >
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
            <button
              type="button"
              className={`mic${listening ? " is-listening" : ""}`}
              onClick={() => setListening((current) => !current)}
              aria-pressed={listening}
              aria-label={listening ? "Stop speaking" : "Speak your message"}
            >
              {listening ? (
                <StopIcon width={22} height={22} />
              ) : (
                <MicIcon width={22} height={22} />
              )}
              <span>{listening ? "Stop" : "Speak"}</span>
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
            {listening && (
              <div className="listening" role="status">
                <span className="wave" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                </span>
                Listening… tap Stop when you are done.
              </div>
            )}
            <textarea
              ref={inputRef}
              value={input}
              placeholder="Paste or type here"
              rows={2}
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
            <button
              type="submit"
              className="send"
              disabled={loading || (!input.trim() && attachments.length === 0)}
              aria-label="Check"
            >
              <SendIcon width={22} height={22} />
              <span>Check</span>
            </button>
          </div>
        </form>
      </div>
      {preview && <Lightbox src={preview} onClose={() => setPreview(null)} />}
    </div>
  );
}
