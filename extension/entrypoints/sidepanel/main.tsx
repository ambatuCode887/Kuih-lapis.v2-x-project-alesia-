import React from 'react';
import ReactDOM from 'react-dom/client';
import Chat from '@/components/Chat';

function openFullTab() {
  browser.tabs.create({ url: browser.runtime.getURL('/app.html') });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Chat onExpand={openFullTab} />
  </React.StrictMode>,
);
