from __future__ import annotations

import functools
import http.server
import json
import shutil
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

pytestmark = pytest.mark.browser

ROOT = Path(__file__).resolve().parents[1]
EXTENSION_DIR = ROOT / "extension" / ".output" / "chrome-mv3"
BACKEND_URL = "http://127.0.0.1:8000"
FILE_SIZE = 8 * 1024 * 1024
CHUNK = 64 * 1024
CHUNK_DELAY_SECONDS = 0.05
# Trusted public host; requires internet access and a running backend.
REMOTE_CLEAN_URL = "https://speed.cloudflare.com/__down?bytes=8388608"
REMOTE_CLEAN_SIZE = 8388608

SNAPSHOT = r"""async () => ({
  downloads: (await chrome.downloads.search({})).map(d => ({
    id: d.id,
    path: d.filename,
    state: d.state,
    paused: d.paused,
    exists: d.exists,
    error: d.error || null,
  })),
  reviews: Object.entries(await chrome.storage.local.get(null))
    .filter(([key]) => key.startsWith('download-review-'))
    .map(([, value]) => value),
})"""


class _SlowSiteHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if not self.path.startswith("/big.bin"):
            super().do_GET()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", 'attachment; filename="big.bin"')
        self.send_header("Content-Length", str(FILE_SIZE))
        self.end_headers()
        block = b"\0" * CHUNK
        try:
            for _ in range(FILE_SIZE // CHUNK):
                self.wfile.write(block)
                time.sleep(CHUNK_DELAY_SECONDS)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *args: Any) -> None:
        pass


@dataclass
class GuardBrowser:
    page: Any
    panel: Any
    service_worker: Any
    downloads: Path

    def state(self) -> dict[str, Any]:
        return self.service_worker.evaluate(SNAPSHOT)


def _backend_up() -> bool:
    try:
        httpx.get(f"{BACKEND_URL}/docs", timeout=2.0)
    except httpx.HTTPError:
        return False
    return True


def _wait_until(getter: Callable[[], Any], timeout: float) -> Any:
    deadline = time.time() + timeout
    while True:
        value = getter()
        if value:
            return value
        if time.time() > deadline:
            raise AssertionError(f"condition not met within {timeout} seconds")
        time.sleep(0.3)


def _item(state: dict[str, Any], download_id: int) -> dict[str, Any]:
    return next(d for d in state["downloads"] if d["id"] == download_id)


def _start_download(g: GuardBrowser) -> int:
    before = {d["id"] for d in g.state()["downloads"]}
    g.page.click("#big")

    def started() -> int | None:
        new = [d["id"] for d in g.state()["downloads"] if d["id"] not in before]
        return new[0] if new else None

    return _wait_until(started, timeout=10)


def _review(g: GuardBrowser, download_id: int) -> dict[str, Any] | None:
    return next(
        (r for r in g.state()["reviews"] if r["downloadId"] == download_id), None
    )


def _click_in_panel(g: GuardBrowser, name: str) -> None:
    g.panel.reload()
    g.panel.get_by_role("button", name=name).click()


def _require_build() -> None:
    if not (EXTENSION_DIR / "manifest.json").exists():
        pytest.skip("Build the extension first: cd extension; npm run build")
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        pytest.skip("Playwright is not installed in this environment.")


@contextmanager
def _launch_guard_browser(workdir: Path, start_url: str) -> Iterator[GuardBrowser]:
    from playwright.sync_api import sync_playwright

    downloads = workdir / "downloads"
    profile = workdir / "profile"
    downloads.mkdir(exist_ok=True)
    (profile / "Default").mkdir(parents=True, exist_ok=True)
    (profile / "Default" / "Preferences").write_text(
        json.dumps(
            {
                "download": {
                    "default_directory": str(downloads),
                    "prompt_for_download": False,
                }
            }
        ),
        encoding="utf-8",
    )
    with sync_playwright() as p:
        if not Path(p.chromium.executable_path).exists():
            pytest.skip("Run .\\.venv\\Scripts\\python -m playwright install chromium first.")
        ctx = p.chromium.launch_persistent_context(
            str(profile),
            headless=False,
            accept_downloads=False,
            args=[
                f"--disable-extensions-except={EXTENSION_DIR}",
                f"--load-extension={EXTENSION_DIR}",
            ],
        )
        try:
            cdp = ctx.browser.new_browser_cdp_session()
            cdp.send(
                "Browser.setDownloadBehavior",
                {
                    "behavior": "allow",
                    "downloadPath": str(downloads),
                    "eventsEnabled": True,
                },
            )
            service_worker = (
                ctx.service_workers[0]
                if ctx.service_workers
                else ctx.wait_for_event("serviceworker", timeout=20000)
            )
            extension_id = service_worker.url.split("/")[2]
            page = ctx.new_page()
            page.goto(start_url)
            panel = ctx.new_page()
            panel.goto(f"chrome-extension://{extension_id}/sidepanel.html")
            yield GuardBrowser(page, panel, service_worker, downloads)
        finally:
            ctx.close()


@pytest.fixture
def guard_browser():
    """Offline group: the backend is down, so the unverified path is used."""
    _require_build()
    if _backend_up():
        pytest.skip("The backend is running, so the unverified path would not be tested.")

    workdir = Path(tempfile.mkdtemp(prefix="download_guard_"))
    site = workdir / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<a id="big" href="big.bin" download>big</a>', encoding="utf-8"
    )
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(_SlowSiteHandler, directory=str(site))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        start_url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
        with _launch_guard_browser(workdir, start_url) as g:
            yield g
    finally:
        server.shutdown()
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture
def live_guard_browser():
    """Live group: the backend is up and the trusted host is reachable."""
    _require_build()
    if not _backend_up():
        pytest.skip("Start the backend on port 8000 to run the live download check.")
    try:
        httpx.head(REMOTE_CLEAN_URL, timeout=10.0, follow_redirects=True)
    except httpx.HTTPError:
        pytest.skip("The trusted test host is not reachable.")

    workdir = Path(tempfile.mkdtemp(prefix="download_guard_live_"))
    try:
        with _launch_guard_browser(workdir, "about:blank") as g:
            yield g
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_download_is_paused_with_unverified_review_and_readable_filename(guard_browser):
    g = guard_browser
    download_id = _start_download(g)

    item = _wait_until(
        lambda: _item(g.state(), download_id)
        if _item(g.state(), download_id)["paused"]
        else None,
        timeout=10,
    )
    assert item["state"] == "in_progress"
    review = _wait_until(lambda: _review(g, download_id), timeout=10)
    assert review["filename"] == "big.bin"

    g.panel.reload()
    body = _wait_until(
        lambda: "We could not check this file" in g.panel.inner_text("body"),
        timeout=10,
    )
    assert body
    _click_in_panel(g, "Stop this download")
    _wait_until(lambda: _item(g.state(), download_id)["state"] == "interrupted", 10)


def test_cancel_in_progress_download_writes_no_file(guard_browser):
    g = guard_browser
    download_id = _start_download(g)
    _wait_until(lambda: _review(g, download_id), timeout=10)

    _click_in_panel(g, "Stop this download")

    item = _wait_until(
        lambda: _item(g.state(), download_id)
        if _item(g.state(), download_id)["state"] == "interrupted"
        else None,
        timeout=10,
    )
    assert _review(g, download_id) is None
    assert not Path(item["path"]).exists()


def test_download_anyway_resumes_and_saves_file(guard_browser):
    g = guard_browser
    download_id = _start_download(g)
    _wait_until(lambda: _review(g, download_id), timeout=10)

    _click_in_panel(g, "Download anyway")

    item = _wait_until(
        lambda: _item(g.state(), download_id)
        if _item(g.state(), download_id)["state"] == "complete"
        else None,
        timeout=60,
    )
    assert Path(item["path"]).stat().st_size == FILE_SIZE
    assert _review(g, download_id) is None


def test_cancel_completed_download_removes_saved_file(guard_browser):
    g = guard_browser
    download_id = _start_download(g)
    _wait_until(lambda: _review(g, download_id), timeout=10)
    _click_in_panel(g, "Download anyway")
    item = _wait_until(
        lambda: _item(g.state(), download_id)
        if _item(g.state(), download_id)["state"] == "complete"
        else None,
        timeout=60,
    )
    saved_path = Path(item["path"])
    assert saved_path.exists()

    # Recreates a review for a file that finished before the guard acted on it.
    g.panel.reload()
    response = g.panel.evaluate(
        """async (id) => {
          await chrome.storage.local.set({
            [`download-review-${id}`]: {
              downloadId: id, filename: 'big.bin', domain: '127.0.0.1',
              status: 'unknown', details: 'test'
            }
          });
          return chrome.runtime.sendMessage({
            type: 'download-review-action', downloadId: id, action: 'cancel'
          });
        }""",
        download_id,
    )

    assert response == {"ok": True}
    removed = _item(g.state(), download_id)
    assert removed["exists"] is False
    assert not saved_path.exists()
    assert _review(g, download_id) is None


def _paused_or_finished(g: GuardBrowser, download_id: int) -> dict[str, Any] | None:
    item = _item(g.state(), download_id)
    return item if item["paused"] or item["state"] != "in_progress" else None


def _settled(g: GuardBrowser, download_id: int) -> dict[str, Any] | None:
    item = _item(g.state(), download_id)
    if item["state"] in ("complete", "interrupted") or _review(g, download_id):
        return item
    return None


@pytest.mark.backend
def test_clean_domain_download_resumes_without_warning(live_guard_browser):
    g = live_guard_browser
    download_id = g.service_worker.evaluate(
        "url => chrome.downloads.download({ url })", REMOTE_CLEAN_URL
    )

    first = _wait_until(lambda: _paused_or_finished(g, download_id), timeout=20)
    if not first["paused"]:
        pytest.skip("The file finished before the guard paused it, so the check did not run.")

    item = _wait_until(lambda: _settled(g, download_id), timeout=120)
    review = _review(g, download_id)
    assert review is None, f"a clean domain should not show a review: {review}"
    assert item["state"] == "complete"
    assert Path(item["path"]).stat().st_size == REMOTE_CLEAN_SIZE


class _StubBackendHandler(http.server.BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send(204, b"", "text/plain")

    def do_GET(self) -> None:
        self._send(404, b"{}", "application/json")

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path.endswith("/sessions"):
            self._send(200, b"{}", "application/json")
            return
        frames = [
            {
                "author": "url_check_agent",
                "customMetadata": {
                    "kind": "domain_stats",
                    "domain": "127.0.0.1",
                    "malicious": 3,
                    "suspicious": 0,
                },
            },
            {
                "author": "url_check_agent",
                "content": {"parts": [{"text": "This domain looks fine to me."}]},
                "turnComplete": True,
            },
        ]
        body = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        self._send(200, body.encode(), "text/event-stream")

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def stub_malicious_browser():
    """Stub backend: VirusTotal counts say malicious while the LLM text says fine."""
    _require_build()
    workdir = Path(tempfile.mkdtemp(prefix="download_guard_stub_"))
    site = workdir / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<a id="big" href="big.bin" download>big</a>', encoding="utf-8"
    )
    site_server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(_SlowSiteHandler, directory=str(site))
    )
    stub_server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StubBackendHandler)
    for server in (site_server, stub_server):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        start_url = f"http://127.0.0.1:{site_server.server_address[1]}/index.html"
        stub_url = f"http://127.0.0.1:{stub_server.server_address[1]}"
        with _launch_guard_browser(workdir, start_url) as g:
            g.service_worker.evaluate(
                "url => chrome.storage.local.set({ 'backend-url': url })", stub_url
            )
            yield g
    finally:
        site_server.shutdown()
        stub_server.shutdown()
        shutil.rmtree(workdir, ignore_errors=True)


def test_flagged_domain_shows_malicious_review_even_if_llm_sees_no_threat(
    stub_malicious_browser,
):
    g = stub_malicious_browser
    download_id = _start_download(g)

    review = _wait_until(lambda: _review(g, download_id), timeout=20)
    assert review["status"] == "malicious", review
    assert "3 engine" in review["details"]
    assert _item(g.state(), download_id)["paused"]

    _click_in_panel(g, "Stop this download")
    _wait_until(lambda: _item(g.state(), download_id)["state"] == "interrupted", 10)
