cd extension
npm run dev
to restart the chrome browser press o + enter
go chrome and click on the puzzle button and select "Cyber Assistant"
"Cyber Assistant" is our extenstion

## Browser download checks

The extension pauses new downloads and checks the source domain with the existing
VirusTotal-backed URL reputation workflow. A domain reported as malicious shows a
warning inside the Cyber Assistant side panel with **Download anyway** and
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
