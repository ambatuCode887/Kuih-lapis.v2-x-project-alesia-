const MENU_SELECTION = 'check-selection';
const MENU_LINK = 'check-link';
// Read and cleared by the chat UI (see components/Chat.tsx).
const PENDING_KEY = 'pending-check';

export default defineBackground(() => {
  // Clicking the toolbar icon opens the side panel.
  browser.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

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
