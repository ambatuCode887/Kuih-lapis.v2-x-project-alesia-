import { askAgent } from '@/lib/api';

const MENU_SELECTION = 'check-selection';
const MENU_LINK = 'check-link';
// Read and cleared by the chat UI (see components/Chat.tsx).
const PENDING_KEY = 'pending-check';
const DOWNLOAD_REVIEW_PREFIX = 'download-review-';

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

function displayFilename(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).at(-1) || 'this download';
}

async function openDownloadReview(review: DownloadReview): Promise<void> {
  const key = reviewKey(review.downloadId);
  await browser.storage.local.set({ [key]: review });

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
    console.warn('The download review is pending; click the Cyber Assistant icon to view it.', error);
    await browser.action.setBadgeBackgroundColor({ color: '#ee5f5b' });
    await browser.action.setBadgeText({ text: '!' });
  }
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
      reply = await askAgent(`Check this domain: ${domain}`);
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

    const clean =
      assessment?.risk_level === 'low' &&
      Boolean(assessment.indicators?.length) &&
      assessment.indicators?.every(
        (indicator) => indicator.verdict?.toLowerCase() === 'clean',
      );
    if (clean) {
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
    if (message.action === 'proceed') {
      await browser.downloads.resume(message.downloadId);
    } else {
      await browser.downloads.cancel(message.downloadId);
    }
    await browser.storage.local.remove(key);
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

export default defineBackground(() => {
  // Clicking the toolbar icon opens the side panel.
  browser.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

  browser.downloads.onCreated.addListener((item) => {
    void inspectDownload(item);
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

  browser.runtime.onInstalled.addListener(() => {
    browser.contextMenus.create({
      id: MENU_SELECTION,
      title: 'Check selected text with Cyber Assistant',
      contexts: ['selection'],
    });
    browser.contextMenus.create({
      id: MENU_LINK,
      title: 'Check this link with Cyber Assistant',
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
