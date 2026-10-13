import { defineConfig } from 'wxt';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'Cyber Assistant',
    description: 'Cybersecurity and scam-awareness assistant in your browser side panel.',
    // unlimitedStorage: pasted screenshots are kept in the saved chat history.
    permissions: ['sidePanel', 'storage', 'unlimitedStorage', 'contextMenus'],
    // Lets the extension call the local ADK server (also skips CORS checks).
    host_permissions: ['http://127.0.0.1:8000/*', 'http://localhost:8000/*'],
    // Needed so the toolbar icon exists and can open the side panel (no popup).
    action: { default_title: 'Open Cyber Assistant' },
  },
});
