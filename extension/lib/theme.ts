import { useEffect, useState } from 'react';

export type Theme = 'light' | 'dark' | 'lilac' | 'black' | 'white';

const THEME_KEY = 'theme';

function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark' || value === 'lilac' || value === 'black' || value === 'white';
}

/** Starts on the saved theme, or "Light" if none is saved. Picks sync between the side panel and the full tab. */
export function useTheme(): {
  theme: Theme;
  toggleTheme: () => void;
  chooseTheme: (next: Theme) => void;
} {
  const [theme, setTheme] = useState<Theme>('white');

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

  function chooseTheme(next: Theme) {
    setTheme(next);
    browser.storage.local.set({ [THEME_KEY]: next });
  }

  return { theme, toggleTheme, chooseTheme };
}
