import { useEffect, useRef, useState } from 'react';
import type { Theme } from '@/lib/theme';

// "light" is the Rosy theme, "dark" is Crimson and "lilac" is Lilac and "black" is Dark (true black). The stored names stay the same,
// so people who already chose a theme keep it.
const OPTIONS: { value: Theme; label: string }[] = [
  { value: 'light', label: 'Rosy' },
  { value: 'dark', label: 'Crimson' },
  { value: 'lilac', label: 'Lilac' },
  { value: 'black', label: 'Dark' },
];

/** A word button, "Appearance", that opens a small menu to pick Rosy, Crimson, Lilac or Dark. */
export default function AppearanceMenu({
  theme,
  onChange,
}: {
  theme: Theme;
  onChange: (next: Theme) => void;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="appearance" ref={root}>
      <button
        type="button"
        className="ghost appearance-btn"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {/* Closed sidebar: a half-sun, half-moon icon. Open sidebar: the word. */}
        <svg
          className="appearance-icon"
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3v18" />
          {/* moon, left half */}
          <path d="M9.6 7.6a4.6 4.6 0 1 0 0 8.8 3.6 3.6 0 0 1 0-8.8z" />
          {/* sun, right half */}
          <circle cx="15.6" cy="12" r="1.7" />
          <path d="M15.6 7.4v.9M15.6 15.7v.9M19.4 12h-.8M18.3 9.3l-.6.6M18.3 14.7l-.6-.6" />
        </svg>
        <span className="appearance-label">Appearance</span>
      </button>
      {open && (
        <div className="appearance-menu" role="group" aria-label="Appearance">
          {OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`appearance-option${theme === option.value ? ' is-on' : ''}`}
              aria-pressed={theme === option.value}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              <span className={`appearance-dot dot-${option.value}`} aria-hidden="true" />
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
