export type NotificationConsent = 'granted' | 'denied';

/** Unset until the user answers the permission popup. Until then no Windows notifications are shown. */
export const NOTIFICATION_CONSENT_KEY = 'notification-consent';

export function isNotificationConsent(value: unknown): value is NotificationConsent {
  return value === 'granted' || value === 'denied';
}
