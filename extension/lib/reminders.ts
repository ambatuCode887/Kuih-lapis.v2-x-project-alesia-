export type ReminderInterval = 'off' | '12h' | '24h';

/** The user's choice from Settings. Falls back to DEFAULT_REMINDER until one is saved. */
export const REMINDER_KEY = 'reminder-interval';
/** The latest reminder, kept until the user dismisses it in the side panel. */
export const REMINDER_TIP_KEY = 'reminder-tip';
export const REMINDER_ALARM = 'awareness-reminder';
export const REMINDER_NOTIFICATION = 'awareness-reminder';

export const REMINDER_OPTIONS: { value: ReminderInterval; label: string }[] = [
  { value: 'off', label: 'Off' },
  { value: '12h', label: 'Every 12 hours' },
  { value: '24h', label: 'Every 24 hours' },
];

export const REMINDER_PERIOD_MINUTES: Record<Exclude<ReminderInterval, 'off'>, number> = {
  '12h': 12 * 60,
  '24h': 24 * 60,
};

// Short nudges to stay alert. They are written by hand, so they never state facts that could be wrong.
const REMINDER_MESSAGES = [
  'Pause before you act on an urgent message. Scammers rely on pressure to make you rush.',
  'Never share a one-time code, even if someone says they are from your bank.',
  'Real companies will not ask for your password by email or chat.',
  'Check where a link really goes before you open it.',
  'A prize, refund or delivery message you did not expect is a common lure. Check through the official app or website.',
  'If someone asks you to move to another app and send money, stop and verify first.',
  'Turn on two-factor authentication for your email and banking accounts.',
  'Someone claiming to be a friend in trouble may be an impostor. Call a number you know before you send money.',
  'Use a different password for every account, and let a password manager remember them.',
  'A screenshot or voice note can be faked. Confirm big requests through a second channel.',
];

export interface ReminderTip {
  message: string;
  at: number;
}

export const DEFAULT_REMINDER: ReminderInterval = '12h';

export function isReminderInterval(value: unknown): value is ReminderInterval {
  return value === 'off' || value === '12h' || value === '24h';
}

export function pickReminderMessage(): string {
  return REMINDER_MESSAGES[Math.floor(Math.random() * REMINDER_MESSAGES.length)]!;
}
