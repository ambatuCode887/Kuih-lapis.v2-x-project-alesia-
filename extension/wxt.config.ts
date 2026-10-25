import { defineConfig } from 'wxt';
import tailwindcss from '@tailwindcss/vite';

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  vite: () => ({ plugins: [tailwindcss()] }),
  manifest: {
    name: 'Project Alesia',
    description: 'Cybersecurity and scam-awareness assistant in your browser side panel.',
    // The side panel API arrived in Chrome 114; 116 adds the fixes the panel relies on.
    minimum_chrome_version: '116',
    // unlimitedStorage: pasted screenshots are kept in the saved chat history.
    // alarms and notifications power the optional awareness reminders (Settings > Reminders).
    permissions: ['sidePanel', 'storage', 'unlimitedStorage', 'contextMenus', 'downloads', 'alarms', 'notifications'],
    // Lets the extension call the local ADK server (also skips CORS checks).
    host_permissions: ['http://127.0.0.1:8000/*', 'http://localhost:8000/*', 'https://kuih-lapis-v2-x-project-alesia.onrender.com/*'],
    // Needed so the toolbar icon exists and can open the side panel (no popup).
    action: { default_title: 'Open Project Alesia' },
  },
});
