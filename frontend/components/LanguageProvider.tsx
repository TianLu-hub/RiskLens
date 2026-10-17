'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import {
  LANGUAGE_STORAGE_KEY,
  parseLocale,
  translate,
  type Locale,
} from '@/lib/translations';

type LanguageContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (text: string, values?: Record<string, string | number>) => string;
};
const LanguageContext = createContext<LanguageContextValue>({
  locale: 'en',
  setLocale: () => {},
  t: (text) => text,
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, updateLocale] = useState<Locale>('en');
  // Hydrate after mount so server/client markup agrees; never overwrite a saved choice during hydration.
  /* eslint-disable react/react-compiler -- Restore optional external browser storage after SSR. */
  useEffect(() => {
    try {
      updateLocale(
        parseLocale(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)),
      );
    } catch {
      /* Storage is optional. */
    }
    const sync = (event: StorageEvent) => {
      if (event.key === LANGUAGE_STORAGE_KEY)
        updateLocale(parseLocale(event.newValue));
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);
  /* eslint-enable react/react-compiler */
  useEffect(() => {
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
  }, [locale]);
  const setLocale = useCallback((next: Locale) => {
    updateLocale(next);
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next);
    } catch {
      /* Switching still works when storage is blocked. */
    }
  }, []);
  const t = useCallback(
    (text: string, values?: Record<string, string | number>) =>
      translate(locale, text, values),
    [locale],
  );
  return (
    <LanguageContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

export function LanguageSwitch() {
  const { locale, setLocale } = useLanguage();
  return (
    <fieldset
      className="flex shrink-0 overflow-hidden rounded border border-border text-xs"
      aria-label="Language / 语言"
    >
      {(['en', 'zh'] as const).map((item) => (
        <button
          key={item}
          type="button"
          lang={item === 'zh' ? 'zh-CN' : 'en'}
          aria-pressed={locale === item}
          onClick={() => setLocale(item)}
          className={`px-2.5 py-2 font-medium ${locale === item ? 'bg-primary/15 text-primary' : 'text-muted-foreground hover:bg-accent'}`}
        >
          {item === 'en' ? 'EN' : '中文'}
        </button>
      ))}
    </fieldset>
  );
}
