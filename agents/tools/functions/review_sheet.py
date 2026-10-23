from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from agents.config import PROJECT_ROOT, env

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
API = "https://sheets.googleapis.com/v4/spreadsheets"
TIMEOUT_SECONDS = 30
_LOCK = threading.Lock()
_CREDENTIALS: service_account.Credentials | None = None


class ReviewSheetError(OSError):
    """The review sheet could not be read or written."""


def is_configured() -> bool:
    return bool(env("REVIEW_SHEET_ID") and env("GOOGLE_SERVICE_ACCOUNT_FILE"))


def _key_path() -> Path:
    configured = Path(env("GOOGLE_SERVICE_ACCOUNT_FILE") or "")
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def _auth_headers() -> dict[str, str]:
    global _CREDENTIALS
    with _LOCK:
        if _CREDENTIALS is None:
            _CREDENTIALS = service_account.Credentials.from_service_account_file(
                str(_key_path()), scopes=SCOPES
            )
        if not _CREDENTIALS.valid:
            _CREDENTIALS.refresh(Request())
        return {"Authorization": f"Bearer {_CREDENTIALS.token}"}


def _call(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    try:
        headers = _auth_headers()
    except (GoogleAuthError, ValueError) as error:
        raise ReviewSheetError(f"Sheets auth failed: {error}") from error
    try:
        response = requests.request(
            method, url, headers=headers, timeout=TIMEOUT_SECONDS, **kwargs
        )
    except requests.RequestException as error:
        raise ReviewSheetError(f"Sheets request failed: {error}") from error
    if response.status_code >= 400:
        raise ReviewSheetError(f"Sheets API returned {response.status_code}: {response.text[:300]}")
    return response.json()


def _values_url(suffix: str) -> str:
    sheet_id = env("REVIEW_SHEET_ID")
    return f"{API}/{sheet_id}/values/{suffix}"


def read_rows() -> tuple[list[str], list[dict[str, str]]]:
    """Return (header, rows) from the first sheet; fully blank rows are skipped."""
    data = _call("GET", _values_url("A:Z"))
    values = data.get("values", [])
    if not values:
        return [], []
    header = [cell.strip() for cell in values[0]]
    rows: list[dict[str, str]] = []
    for raw in values[1:]:
        padded = list(raw) + [""] * (len(header) - len(raw))
        if not any(cell.strip() for cell in padded):
            continue
        rows.append(dict(zip(header, padded)))
    return header, rows


def append_row(values: list[str]) -> None:
    """Append one row in column order; RAW input stores text without formula evaluation."""
    _call(
        "POST",
        _values_url("A1:append"),
        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
        json={"values": [values]},
    )
