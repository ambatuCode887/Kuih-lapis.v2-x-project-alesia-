import { useEffect, useState } from 'react';

export type Theme = 'light' | 'dark';

const THEME_KEY = 'theme';

function systemTheme(): Theme {
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark';
}

/**
 * Light or dark mode. Starts from the system setting until the user picks one,
 * then remembers the choice and keeps the side panel and full tab in step.
 */
export function useTheme(): { theme: Theme; toggleTheme: () => void } {
  const [theme, setTheme] = useState<Theme>(systemTheme);

  useEffect(() => {
    browser.storage.local.get(THEME_KEY).then((result) => {
      const saved = result[THEME_KEY];
      if (isTheme(saved)) setTheme(saved);
    });

    const onChange = (changes: Record<string, { newValue?: unknown }>, area: string) => {
      const next = changes[THEME_KEY]?.newValue;
      if (area === 'local' && isTheme(next)) setTheme(next);
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  function toggleTheme() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    browser.storage.local.set({ [THEME_KEY]: next });
  }

  return { theme, toggleTheme };
}
