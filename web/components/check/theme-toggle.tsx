"use client";

import { useEffect, useRef, useState } from "react";

type Theme = "light" | "dark" | "lilac" | "black";
const KEY = "cyber-assistant-theme";

// "light" is Rosy, "dark" is Crimson and "lilac" is Lilac. The stored names stay the same.
const OPTIONS: { value: Theme; label: string }[] = [
  { value: "light", label: "Rosy" },
  { value: "dark", label: "Crimson" },
  { value: "lilac", label: "Lilac" },
  { value: "black", label: "Dark" },
];

/**
 * A word button, "Appearance", that opens a small menu to pick Rosy, Crimson, Lilac or Dark.
 * The choice is remembered, and the landing page is put back to Rosy when you leave.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(KEY);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (saved === "light" || saved === "dark" || saved === "lilac" || saved === "black") setTheme(saved);
    } catch {
      // storage unavailable: stay on Rosy
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    return () => {
      document.documentElement.dataset.theme = "light";
    };
  }, [theme]);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function choose(next: Theme) {
    setTheme(next);
    setOpen(false);
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      // not saved, still switches for this visit
    }
  }

  return (
    <div className="fixed bottom-4 left-4 z-40" ref={root}>
      <button
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="dark-glass min-h-11 rounded-full border px-5 text-sm font-bold text-white/90 shadow-xl transition-colors hover:text-[#f2c7c2]"
      >
        Appearance
      </button>
      {open && (
        <div
          role="group"
          aria-label="Appearance"
          className="absolute bottom-full left-0 z-50 mb-2 flex min-w-44 flex-col gap-1 rounded-2xl border-2 border-line-strong bg-card p-1.5 text-ink shadow-2xl"
        >
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={theme === option.value}
              onClick={() => choose(option.value)}
              className={`flex min-h-11 items-center gap-3 rounded-xl px-3 text-base font-semibold transition-colors hover:bg-jade/15 ${
                theme === option.value ? "bg-jade/25 ring-2 ring-jade" : ""
              }`}
            >
              <span
                aria-hidden
                className="size-5 rounded-full border-2 border-line-strong"
                style={{
                  background:
                    option.value === "light"
                      ? "linear-gradient(135deg, #faf4ed 50%, #d7827e 50%)"
                      : option.value === "dark"
                        ? "linear-gradient(135deg, #150b0f 50%, #e5566d 50%)"
                        : option.value === "lilac"
                          ? "linear-gradient(135deg, #eff1f5 50%, #8839ef 50%)"
                          : "linear-gradient(135deg, #000 50%, #d4d4d4 50%)",
                }}
              />
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
