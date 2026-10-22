cd extension
npm run dev
to restart the chrome browser press o + enter
go chrome and click on the puzzle button and select "Project Alesia"
"Project Alesia" is our extenstion

## Browser download checks

The extension pauses new downloads and checks the source domain with the existing
VirusTotal-backed URL reputation workflow. A domain reported as malicious shows a
warning inside the Project Alesia side panel with **Download anyway** and
**Cancel download** actions. A clean reputation result resumes the download
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

- **Awareness reminders**: choose **Off** (the default), **Every 12 hours**, or
  **Every 24 hours**. A reminder shows a short cybersecurity or scam awareness tip
  as a Windows notification (it stays on screen until dismissed) and as an "Awareness tip"
  toast over the top of the panel until you choose **Got it**. The toast only appears while
  the side panel is open. Reminders are not sent while Chrome is closed.
- **Appearance**: pick one of the five colour themes.

The reminder schedule uses the `alarms` permission and notifications use the
`notifications` permission. The reminder tips are fixed messages in
[lib/reminders.ts](lib/reminders.ts), not live answers from the agent.