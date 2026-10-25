import { useEffect, useState } from 'react';
import {
  NOTIFICATION_CONSENT_KEY,
  isNotificationConsent,
  type NotificationConsent,
} from '@/lib/notification-consent';
import { AlertIcon } from './Icons';
import './download-warning.css';

/**
 * Asks once, on open, whether Project Alesia may send Windows notifications.
 * It shows again only while no answer is saved. Settings can change the answer later.
 */
export default function NotificationConsentDialog() {
  const [consent, setConsent] = useState<NotificationConsent | 'unset' | 'loading'>('loading');
  const [blockedNote, setBlockedNote] = useState('');

  useEffect(() => {
    browser.storage.local.get(NOTIFICATION_CONSENT_KEY).then((result) => {
      const stored = result[NOTIFICATION_CONSENT_KEY];
      setConsent(isNotificationConsent(stored) ? stored : 'unset');
    });

    const onChange = (
      changes: Record<string, { newValue?: unknown }>,
      area: string,
    ) => {
      if (area !== 'local' || !(NOTIFICATION_CONSENT_KEY in changes)) return;
      const next = changes[NOTIFICATION_CONSENT_KEY]?.newValue;
      setConsent(isNotificationConsent(next) ? next : 'unset');
    };
    browser.storage.onChanged.addListener(onChange);
    return () => browser.storage.onChanged.removeListener(onChange);
  }, []);

  async function answer(choice: NotificationConsent) {
    await browser.storage.local.set({ [NOTIFICATION_CONSENT_KEY]: choice });
    if (choice === 'granted') {
      // Chrome has its own switch for notifications; the extension cannot turn it on. Check it so the user knows.
      const levelApi = browser.notifications as typeof browser.notifications & {
        getPermissionLevel?: () => Promise<string>;
      };
      const level = await levelApi.getPermissionLevel?.().catch(() => undefined);
      if (level === 'denied') {
        setBlockedNote(
          'Chrome is blocking notifications. Turn them on in Windows Settings > System > Notifications, then allow Google Chrome.',
        );
        return;
      }
    }
    setConsent(choice);
  }

  if (consent !== 'unset') return null;

  return (
    <div className="download-warning-overlay">
      <section
        className="warning"
        role="dialog"
        aria-modal="true"
        aria-labelledby="notification-consent-title"
      >
        <div className="warning__badge" aria-hidden="true">
          <AlertIcon />
        </div>
        <h2 id="notification-consent-title">Allow notifications?</h2>
        <p>
          Project Alesia can send Windows notifications for two things: safety reminders
          you choose in Settings, and warnings when a download may be unsafe. You can
          change this later in Settings.
        </p>
        <p className="warning__muted">Warnings still appear in this panel either way.</p>
        {blockedNote && <p className="warning__error" role="alert">{blockedNote}</p>}
        <div className="warning__actions">
          <button
            autoFocus
            className="warning__proceed"
            onClick={() => void answer('granted')}
            type="button"
          >
            Allow notifications
          </button>
          <button
            className="warning__cancel"
            onClick={() => void answer('denied')}
            type="button"
          >
            Not now
          </button>
        </div>
        {blockedNote && (
          <button
            className="warning__proceed"
            onClick={() => setConsent('granted')}
            type="button"
          >
            Continue
          </button>
        )}
      </section>
    </div>
  );
}
