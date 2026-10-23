# Project Alesia extension

Project Alesia is the browser extension: a WXT and React side panel. It sends questions to the backend API server, so start the backend first (see section 6 of the [main README](../README.md)).

## Setup and run

```powershell
cd extension
npm install
npm run dev
```

- `npm install` also runs `wxt prepare` (postinstall).
- `npm run dev` starts Chrome with the extension loaded. To restart the Chrome browser, press o + enter.
- If the extension is not visible, go to Chrome, click the puzzle button, and select "Project Alesia".

## Build and checks

```powershell
npm run build
npm run typecheck
npm run lint
```

`npm run build` writes the unpacked extension to `extension/.output/chrome-mv3`. To load it manually, open `chrome://extensions`, turn on Developer mode, and choose **Load unpacked**.

The extension calls the backend at `http://127.0.0.1:8000` while `USE_BACKEND` in `lib/api.ts` is `true`. If the backend is not running, the chat shows "Can't reach the backend" with a reminder to start `adk api_server`. When `USE_BACKEND` is `false`, the extension shows fixed sample replies instead.

## Browser download checks

The extension pauses new downloads and checks the source domain with the existing
VirusTotal-backed URL reputation workflow. A domain reported as malicious shows a
warning inside the Project Alesia side panel with **Download anyway** and
**Stop this download** actions. A clean reputation result resumes the download
without showing a warning. If the reputation check is inconclusive or unavailable,
the download stays paused and the same actions are shown so the user can decide.
The extension attempts to open the side panel automatically; if Chrome blocks
that programmatic opening, the extension icon is marked and the pending warning
appears when the side panel is opened.

This is a source-domain reputation check, not a scan of the downloaded file's
contents. Signed or private download URLs are not sent to VirusTotal; only the
hostname is checked. As with other asynchronous browser download events, pausing
is best-effort and is not an atomic guarantee that no bytes have been written
before the check begins. Chrome's own download protection remains enabled.

## Settings and awareness reminders

Open **Settings** in the side panel (or the full tab) to:

- **Awareness reminders**: choose **Every 12 hours** (the default), **Every 24 hours**, or
  **Off**, then select **Save**. A reminder shows a short cybersecurity or scam awareness tip
  as a Windows notification (it stays on screen until dismissed) and as an "Awareness tip"
  toast over the top of the panel until you choose **Got it**. The toast only appears while
  the side panel is open. Reminders are not sent while Chrome is closed.
- **Appearance**: pick one of the five colour themes.

The reminder schedule uses the `alarms` permission and notifications use the
`notifications` permission. The reminder tips are fixed messages in
[lib/reminders.ts](lib/reminders.ts), not live answers from the agent.
