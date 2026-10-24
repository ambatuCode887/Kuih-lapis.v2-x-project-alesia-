import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Speech to text for the message box, using the browser's built-in recognition.
 *
 * Note for the privacy policy: in Chrome this sends the audio to Google's servers to be
 * turned into text. It only starts when the user presses the microphone button.
 */

export type SpeechLang = 'en-MY' | 'ms-MY';

export const SPEECH_LANGUAGES: { value: SpeechLang; label: string }[] = [
  { value: 'en-MY', label: 'English' },
  { value: 'ms-MY', label: 'Bahasa Malaysia' },
];

export type SpeechProblem =
  | 'blocked' // the microphone permission was denied or is not available here
  | 'no-mic' // no microphone was found
  | 'network' // the speech service could not be reached
  | 'quiet' // nothing was heard
  | 'failed';

const LANG_KEY = 'speech-lang';

// The browser API has no TypeScript types in every setup, so describe the part we use.
interface RecognitionAlternative {
  transcript: string;
}
interface RecognitionResult {
  0: RecognitionAlternative;
  length: number;
}
interface RecognitionEvent {
  results: ArrayLike<RecognitionResult>;
}
interface RecognitionErrorEvent {
  error: string;
}
interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: RecognitionEvent) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type RecognitionConstructor = new () => Recognition;

function recognitionConstructor(): RecognitionConstructor | null {
  const scope = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null;
}

function savedLanguage(): SpeechLang {
  try {
    const saved = window.localStorage.getItem(LANG_KEY);
    if (saved === 'en-MY' || saved === 'ms-MY') return saved;
  } catch {
    // storage is optional
  }
  return 'en-MY';
}

function problemFor(error: string): SpeechProblem | null {
  switch (error) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'blocked';
    case 'audio-capture':
      return 'no-mic';
    case 'network':
      return 'network';
    case 'no-speech':
      return 'quiet';
    case 'aborted':
      return null; // we stopped it ourselves
    default:
      return 'failed';
  }
}

/**
 * @param getText reads what is in the message box right now, so spoken words are added to the end.
 * @param onText  receives the full text (what was already there plus what was heard).
 */
export function useSpeechInput(getText: () => string, onText: (text: string) => void) {
  const [supported] = useState(() => recognitionConstructor() !== null);
  const [listening, setListening] = useState(false);
  const [problem, setProblem] = useState<SpeechProblem | null>(null);
  const [lang, setLangState] = useState<SpeechLang>(savedLanguage);

  const recognition = useRef<Recognition | null>(null);
  const base = useRef('');
  const langRef = useRef(lang);
  const getTextRef = useRef(getText);
  const onTextRef = useRef(onText);
  getTextRef.current = getText;
  onTextRef.current = onText;

  const stop = useCallback(() => {
    recognition.current?.stop();
  }, []);

  const start = useCallback(() => {
    const Ctor = recognitionConstructor();
    if (!Ctor || recognition.current) return;

    setProblem(null);
    const current = getTextRef.current();
    // Add a space between what was typed and what is spoken.
    base.current = current && !/\s$/.test(current) ? `${current} ` : current;

    const next = new Ctor();
    next.lang = langRef.current;
    next.continuous = true;
    next.interimResults = true;
    next.onstart = () => setListening(true);
    next.onresult = (event) => {
      let heard = '';
      for (let i = 0; i < event.results.length; i += 1) {
        heard += event.results[i]?.[0]?.transcript ?? "";
      }
      onTextRef.current(base.current + heard.trimStart());
    };
    next.onerror = (event) => {
      const found = problemFor(event.error);
      if (found) setProblem(found);
    };
    next.onend = () => {
      recognition.current = null;
      setListening(false);
    };
    recognition.current = next;
    try {
      next.start();
    } catch {
      recognition.current = null;
      setProblem('failed');
    }
  }, []);

  const toggle = useCallback(() => {
    if (recognition.current) stop();
    else start();
  }, [start, stop]);

  /** Change the spoken language. If it is listening, it restarts in the new language. */
  const setLang = useCallback(
    (next: SpeechLang) => {
      setLangState(next);
      langRef.current = next;
      try {
        window.localStorage.setItem(LANG_KEY, next);
      } catch {
        // not remembered, still works for now
      }
      if (recognition.current) {
        recognition.current.onend = () => {
          recognition.current = null;
          setListening(false);
          start();
        };
        recognition.current.stop();
      }
    },
    [start],
  );

  // Never leave the microphone open when the panel goes away.
  useEffect(
    () => () => {
      if (recognition.current) {
        recognition.current.onend = null;
        recognition.current.abort();
        recognition.current = null;
      }
    },
    [],
  );

  return { supported, listening, problem, lang, setLang, start, stop, toggle, clearProblem: () => setProblem(null) };
}

export const SPEECH_PROBLEM_TEXT: Record<SpeechProblem, string> = {
  blocked:
    'The microphone is blocked. Allow it when Chrome asks, or open Project Alesia in a full tab once and allow it there.',
  'no-mic': 'No microphone was found. Plug one in and try again.',
  network: 'The speech service could not be reached. Check your internet and try again.',
  quiet: 'I did not hear anything. Press the microphone and try again.',
  failed: 'Speech to text did not work this time. You can still type your message.',
};
