import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";
import type { Theme } from "@/lib/theme";
import {
  DEFAULT_REMINDER,
  REMINDER_KEY,
  REMINDER_OPTIONS,
  isReminderInterval,
  type ReminderInterval,
} from "@/lib/reminders";
import { GearIcon } from "./Icons";

const MENU_WIDTH = 280;
const MENU_EDGE = 12;
const MENU_GAP = 6;

// Stored theme names are unchanged, so existing choices carry over. Labels: light = Rosy, dark = Crimson, black = Dark, white = Light.
const THEME_OPTIONS: { value: Theme; label: string }[] = [
  { value: "light", label: "Rosy" },
  { value: "dark", label: "Crimson" },
  { value: "lilac", label: "Lilac" },
  { value: "black", label: "Dark" },
  { value: "white", label: "Light" },
];

function useReminderInterval(): {
  draft: ReminderInterval;
  saved: ReminderInterval;
  setDraft: (next: ReminderInterval) => void;
  revertDraft: () => void;
  saveDraft: () => void;
} {
  const [saved, setSaved] = useState<ReminderInterval>(DEFAULT_REMINDER);
  const [draft, setDraft] = useState<ReminderInterval>(DEFAULT_REMINDER);

  useEffect(() => {
    browser.storage.local.get(REMINDER_KEY).then((result) => {
      const stored = result[REMINDER_KEY];
      const value = isReminderInterval(stored) ? stored : DEFAULT_REMINDER;
      setSaved(value);
      setDraft(value);
    });

    const onChange = (
      changes: Record<string, { newValue?: unknown }>,
      area: string,
    ) => {
      if (area !== "local" || !(REMINDER_KEY in changes)) return;
      const next = changes[REMINDER_KEY]?.newValue;
      const value = isReminderInterval(next) ? next : DEFAULT_REMINDER;
      setSaved(value);
      setDraft(value);
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, []);

  function saveDraft() {
    setSaved(draft);
    void browser.storage.local.set({ [REMINDER_KEY]: draft });
  }

  function revertDraft() {
    setDraft(saved);
  }

  return { draft, saved, setDraft, revertDraft, saveDraft };
}

/**
 * A "Settings" button that opens a small panel: awareness reminders (off, every 12 or 24 hours)
 * and the colour theme.
 */
export default function SettingsMenu({
  theme,
  onChangeTheme,
}: {
  theme: Theme;
  onChangeTheme: (next: Theme) => void;
}) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<CSSProperties>({});
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const { draft, saved, setDraft, revertDraft, saveDraft } =
    useReminderInterval();

  // The menu is rendered in <body> so the sidebar's clipping and blur containers cannot cut it off.
  // It opens above the button, which sits at the bottom of the sidebar.
  useLayoutEffect(() => {
    if (!open || !button.current) return;
    const rect = button.current.getBoundingClientRect();
    const width = Math.min(MENU_WIDTH, window.innerWidth - MENU_EDGE * 2);
    setPosition({
      left: Math.max(
        MENU_EDGE,
        Math.min(rect.left, window.innerWidth - width - MENU_EDGE),
      ),
      bottom: window.innerHeight - rect.top + MENU_GAP,
      width,
      maxHeight: Math.max(
        160,
        Math.min(
          rect.top - MENU_GAP - MENU_EDGE,
          window.innerHeight * 0.7,
          480,
        ),
      ),
    });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!root.current?.contains(target) && !menu.current?.contains(target))
        setOpen(false);
    };
    const onResize = () => setOpen(false);
    window.addEventListener("resize", onResize);
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("resize", onResize);
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="settings" ref={root}>
      <button
        ref={button}
        type="button"
        className="ghost settings-btn"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => {
          if (!open) revertDraft();
          setOpen(!open);
        }}
      >
        <GearIcon className="settings-icon" width={22} height={22} />
        <span className="settings-label">Settings</span>
      </button>
      {open &&
        createPortal(
          <div
            ref={menu}
            className="settings-menu"
            style={position}
            role="dialog"
            aria-label="Settings"
          >
            <section
              className="settings-section"
              aria-labelledby="settings-reminders-title"
            >
              <h3 id="settings-reminders-title" className="settings-heading">
                Awareness reminders
              </h3>
              <p className="settings-hint">
                A short safety tip as a notification.
              </p>
              <div
                className="settings-list"
                role="radiogroup"
                aria-labelledby="settings-reminders-title"
              >
                {REMINDER_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    role="radio"
                    className={`settings-option${draft === option.value ? " is-on" : ""}`}
                    aria-checked={draft === option.value}
                    onClick={() => setDraft(option.value)}
                  >
                    <span className="settings-radio" aria-hidden="true" />
                    {option.label}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="settings-save"
                disabled={draft === saved}
                onClick={saveDraft}
              >
                Save
              </button>
            </section>
            <section
              className="settings-section"
              aria-labelledby="settings-appearance-title"
            >
              <h3 id="settings-appearance-title" className="settings-heading">
                Appearance
              </h3>
              <div
                className="settings-themes"
                role="group"
                aria-labelledby="settings-appearance-title"
              >
                {THEME_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`appearance-option${theme === option.value ? " is-on" : ""}`}
                    aria-pressed={theme === option.value}
                    onClick={() => onChangeTheme(option.value)}
                  >
                    <span
                      className={`appearance-dot dot-${option.value}`}
                      aria-hidden="true"
                    />
                    {option.label}
                  </button>
                ))}
              </div>
            </section>
          </div>,
          document.body,
        )}
    </div>
  );
}
