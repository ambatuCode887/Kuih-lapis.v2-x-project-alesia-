import { askAgent } from '@/lib/api';
import { isCleanDomain } from '@/lib/domainStats';
import {
  REMINDER_ALARM,
  REMINDER_KEY,
  REMINDER_NOTIFICATION,
  REMINDER_PERIOD_MINUTES,
  REMINDER_TIP_KEY,
  isReminderInterval,
  pickReminderMessage,
  type ReminderInterval,
  type ReminderTip,
} from '@/lib/reminders';

const MENU_SELECTION = 'check-selection';
const MENU_LINK = 'check-link';
// Read and cleared by the chat UI (see components/Chat.tsx).
const PENDING_KEY = 'pending-check';
const DOWNLOAD_REVIEW_PREFIX = 'download-review-';
const DOWNLOAD_NOTIFICATION_PREFIX = 'download-review-alert-';

interface DownloadReview {
  downloadId: number;
  filename: string;
  domain: string;
  status: 'malicious' | 'unknown';
  details: string;
}

interface DownloadReviewAction {
  type: 'download-review-action';
  downloadId: number;
  action: 'proceed' | 'cancel';
}

function reviewKey(downloadId: number): string {
  return `${DOWNLOAD_REVIEW_PREFIX}${downloadId}`;
}

function reviewNotificationId(downloadId: number): string {
  return `${DOWNLOAD_NOTIFICATION_PREFIX}${downloadId}`;
}

function downloadIdFromNotification(id: string): number | null {
  if (!id.startsWith(DOWNLOAD_NOTIFICATION_PREFIX)) return null;
  const value = Number(id.slice(DOWNLOAD_NOTIFICATION_PREFIX.length));
  return Number.isInteger(value) ? value : null;
}

function displayFilename(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).at(-1) || 'this download';
}

async function openDownloadReview(review: DownloadReview): Promise<void> {
  const key = reviewKey(review.downloadId);
  const [current] = await browser.downloads.search({ id: review.downloadId });
  const filename = current?.filename ? displayFilename(current.filename) : review.filename;
  await browser.storage.local.set({ [key]: { ...review, filename } });

  try {
    const [activeTab] = await browser.tabs.query({
      active: true,
      lastFocusedWindow: true,
    });
    if (activeTab?.id === undefined) {
      throw new Error('There is no active browser tab to open the side panel for.');
    }
    await browser.sidePanel.open({ tabId: activeTab.id });
  } catch (error) {
    console.warn('The download review is pending; click the Project Alesia icon to view it.', error);
    await browser.action.setBadgeBackgroundColor({ color: '#ee5f5b' });
    await browser.action.setBadgeText({ text: '!' });
  }

  await browser.notifications
    .create(reviewNotificationId(review.downloadId), {
      type: 'basic',
      iconUrl: browser.runtime.getURL('/icon/128.png'),
      title: review.status === 'malicious' ? 'Malicious download stopped' : 'Unverified download paused',
      message: `${filename} from ${review.domain || 'an unknown source'}. ${review.details}`,
      requireInteraction: true,
      buttons: [{ title: 'Stop this download' }, { title: 'Download anyway' }],
    })
    .catch((error) => console.warn('Could not show the download notification.', error));
}

async function inspectDownload(
  item: Browser.downloads.DownloadItem,
): Promise<void> {
  try {
    await browser.downloads.pause(item.id);
    const [pausedItem] = await browser.downloads.search({ id: item.id });
    if (!pausedItem?.paused || pausedItem.state !== 'in_progress') {
      console.error(`Could not pause download ${item.id} before reputation check.`);
      return;
    }

    let domain = '';
    let reply;
    try {
      const url = new URL(item.url);
      if (url.protocol !== 'http:' && url.protocol !== 'https:') {
        throw new Error('This download does not have an HTTP or HTTPS source domain.');
      }
      domain = url.hostname;
      reply = await askAgent(`Check download source: ${domain}`);
    } catch (error) {
      await openDownloadReview({
        downloadId: item.id,
        filename: displayFilename(item.filename),
        domain,
        status: 'unknown',
        details:
          error instanceof Error
            ? error.message
            : 'The download source could not be checked.',
      });
      return;
    }

    const assessment = reply.assessment;
    if (assessment?.indicators?.some(
      (indicator) => indicator.verdict?.toLowerCase() === 'malicious',
    )) {
      await openDownloadReview({
        downloadId: item.id,
        filename: displayFilename(item.filename),
        domain,
        status: 'malicious',
        details:
          assessment.assessment ??
          'The download source domain was reported as malicious.',
      });
      return;
    }

    if (reply.domainStats && reply.domainStats.malicious > 0) {
      await openDownloadReview({
        downloadId: item.id,
        filename: displayFilename(item.filename),
        domain,
        status: 'malicious',
        details: `VirusTotal reported this domain as malicious (${reply.domainStats.malicious} engine(s)).`,
      });
      return;
    }

    if (isCleanDomain(reply.domainStats)) {
        try {
          await browser.downloads.resume(item.id);
        } catch (error) {
          await openDownloadReview({
            downloadId: item.id,
            filename: displayFilename(item.filename),
            domain,
            status: 'unknown',
            details:
              error instanceof Error
                ? `The domain check was clean, but the browser could not resume the download: ${error.message}`
                : 'The domain check was clean, but the browser could not resume the download.',
          });
        }
        return;
      }

    await openDownloadReview({
      downloadId: item.id,
      filename: displayFilename(item.filename),
      domain,
      status: 'unknown',
      details:
        assessment?.assessment ??
        reply.text ??
        'The download source could not be verified.',
    });
  } catch (error) {
    console.error(`Could not inspect download ${item.id}.`, error);
  }
}

async function handleDownloadReviewAction(
  message: DownloadReviewAction,
): Promise<{ ok: boolean; error?: string }> {
  const key = reviewKey(message.downloadId);
  const result = await browser.storage.local.get(key);
  const review = result[key] as DownloadReview | undefined;
  if (!review || review.downloadId !== message.downloadId) {
    return { ok: false, error: 'This download review is no longer available.' };
  }

  try {
    const [item] = await browser.downloads.search({ id: message.downloadId });
    const saved = item?.state === 'complete';
    if (message.action === 'proceed') {
      // A completed download is already saved, so there is nothing to resume.
      if (!saved) await browser.downloads.resume(message.downloadId);
    } else if (saved) {
      await browser.downloads.removeFile(message.downloadId);
    } else {
      await browser.downloads.cancel(message.downloadId);
    }
    await browser.storage.local.remove(key);
    await browser.notifications.clear(reviewNotificationId(message.downloadId));
    return { ok: true };
  } catch (error) {
    return {
      ok: false,
      error:
        error instanceof Error
          ? error.message
          : 'The download could not be updated.',
    };
  }
}

async function updateReviewFilename(downloadId: number, filename: string): Promise<void> {
  const key = reviewKey(downloadId);
  const stored = await browser.storage.local.get(key);
  const review = stored[key] as DownloadReview | undefined;
  if (!review || review.filename === filename) return;
  await browser.storage.local.set({ [key]: { ...review, filename } });
}

/**
 * Close the side panel. The panel is shared by every tab, so when "Expand" opens the
 * full-page view the panel would otherwise stay open beside it. Turning the panel off
 * closes it; turning it back on lets the toolbar icon open it again. This runs here,
 * not in the panel itself, because the panel page is gone as soon as it closes.
 */
async function closeSidePanel(): Promise<void> {
  await browser.sidePanel.setOptions({ enabled: false });
  await new Promise((resolve) => setTimeout(resolve, 150));
  await browser.sidePanel.setOptions({ enabled: true });
}

async function readReminderInterval(): Promise<ReminderInterval> {
  const stored = await browser.storage.local.get(REMINDER_KEY);
  const value = stored[REMINDER_KEY];
  return isReminderInterval(value) ? value : 'off';
}

/**
 * Make the alarm match the chosen interval. Unless forced, an alarm that already has the
 * right period is kept, so restarting this background script does not reset the timer.
 */
async function syncReminderAlarm(interval: ReminderInterval, force = false): Promise<void> {
  const existing = await browser.alarms.get(REMINDER_ALARM);
  if (interval === 'off') {
    if (existing) await browser.alarms.clear(REMINDER_ALARM);
    return;
  }
  const period = REMINDER_PERIOD_MINUTES[interval];
  if (!force && existing?.periodInMinutes === period) return;
  await browser.alarms.create(REMINDER_ALARM, { periodInMinutes: period });
}

async function showReminder(): Promise<void> {
  const message = pickReminderMessage();
  const tip: ReminderTip = { message, at: Date.now() };
  await browser.storage.local.set({ [REMINDER_TIP_KEY]: tip });
  await browser.notifications.create(REMINDER_NOTIFICATION, {
    type: 'basic',
    iconUrl: browser.runtime.getURL('/icon/128.png'),
    title: 'Project Alesia reminder',
    message,
    requireInteraction: true,
  });
}

export default defineBackground(() => {
  // Clicking the toolbar icon opens the side panel.
  browser.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

  // Service workers restart often, so re-check the schedule instead of assuming it survived.
  void readReminderInterval().then((interval) => syncReminderAlarm(interval));

  browser.runtime.onMessage.addListener((message: unknown) => {
    if ((message as { type?: string } | null)?.type !== 'close-side-panel') return;
    return closeSidePanel().then(
      () => ({ ok: true }),
      (error: unknown) => ({ ok: false, error: String(error) }),
    );
  });

  browser.downloads.onCreated.addListener((item) => {
    void inspectDownload(item);
  });

  browser.downloads.onChanged.addListener((delta) => {
    if (!delta.filename?.current) return;
    void updateReviewFilename(delta.id, displayFilename(delta.filename.current));
  });

  browser.runtime.onMessage.addListener((message: unknown) => {
    if (!message || typeof message !== 'object') return;
    const action = message as Partial<DownloadReviewAction>;
    if (
      action.type !== 'download-review-action' ||
      typeof action.downloadId !== 'number' ||
      (action.action !== 'proceed' && action.action !== 'cancel')
    ) {
      return;
    }
    return handleDownloadReviewAction(action as DownloadReviewAction);
  });

  browser.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name !== REMINDER_ALARM) return;
    void (async () => {
      // The setting can change between scheduling and firing, so check it again.
      if ((await readReminderInterval()) === 'off') {
        await browser.alarms.clear(REMINDER_ALARM);
        return;
      }
      await showReminder();
    })();
  });

  browser.storage.onChanged.addListener((changes, area) => {
    if (area !== 'local' || !(REMINDER_KEY in changes)) return;
    const next = changes[REMINDER_KEY]?.newValue;
    void syncReminderAlarm(isReminderInterval(next) ? next : 'off', true);
  });

  browser.notifications.onClicked.addListener((id) => {
    if (id === REMINDER_NOTIFICATION) void browser.notifications.clear(id);
  });

  browser.notifications.onButtonClicked.addListener((id, buttonIndex) => {
    const downloadId = downloadIdFromNotification(id);
    if (downloadId === null) return;
    // Button 0 is "Stop this download"; button 1 is "Download anyway".
    void handleDownloadReviewAction({
      type: 'download-review-action',
      downloadId,
      action: buttonIndex === 0 ? 'cancel' : 'proceed',
    });
  });

  browser.runtime.onInstalled.addListener(() => {
    browser.contextMenus.create({
      id: MENU_SELECTION,
      title: 'Check selected text with Project Alesia',
      contexts: ['selection'],
    });
    browser.contextMenus.create({
      id: MENU_LINK,
      title: 'Check this link with Project Alesia',
      contexts: ['link'],
    });
  });

  browser.contextMenus.onClicked.addListener((info, tab) => {
    let prompt: string | null = null;
    if (info.menuItemId === MENU_SELECTION && info.selectionText) {
      prompt = `Analyze this message: "${info.selectionText.trim()}"`;
    } else if (info.menuItemId === MENU_LINK && info.linkUrl) {
      prompt = `Check this link: ${info.linkUrl}`;
    }
    if (!prompt) return;

    // Open the panel first: Chrome only allows it directly inside the click.
    if (tab?.id !== undefined) {
      browser.sidePanel.open({ tabId: tab.id });
    }
    browser.storage.local.set({ [PENDING_KEY]: { prompt, at: Date.now() } });
  });
});
