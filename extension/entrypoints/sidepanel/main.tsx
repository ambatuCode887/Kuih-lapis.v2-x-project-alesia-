import React from 'react';
import ReactDOM from 'react-dom/client';
import Chat from '@/components/Chat';

/**
 * Open the full-page view, then close the side panel so the two are not side by
 * side. If the full page is already open in another tab, switch to it instead of
 * opening a second copy.
 */
async function openFullTab() {
  const url = browser.runtime.getURL('/app.html');

  let existing: Browser.tabs.Tab | undefined;
  try {
    [existing] = await browser.tabs.query({ url });
  } catch {
    // Without access to tab URLs we simply open a new tab.
  }

  if (existing?.id !== undefined) {
    await browser.tabs.update(existing.id, { active: true });
    await browser.windows.update(existing.windowId, { focused: true });
  } else {
    await browser.tabs.create({ url });
  }

  // The background script closes the panel (see closeSidePanel in background.ts).
  void browser.runtime.sendMessage({ type: 'close-side-panel' });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Chat onExpand={openFullTab} />
  </React.StrictMode>,
);
