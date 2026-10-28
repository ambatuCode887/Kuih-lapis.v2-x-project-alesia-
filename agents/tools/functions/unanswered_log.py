from __future__ import annotations

import csv
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from agents.config import PROJECT_ROOT, env
from agents.tools.functions import review_sheet

FIELDS = ["timestamp_utc", "question", "model_answer", "status"]
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_LOCK = threading.Lock()
logger = logging.getLogger(__name__)


def unanswered_log_path() -> Path:
    configured = env("UNANSWERED_LOG_PATH")
    if not configured:
        return PROJECT_ROOT / "data" / "unanswered_questions.csv"
    path = Path(configured)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _safe_cell(value: str) -> str:
    # Spreadsheets would evaluate these prefixes as formulas.
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def append_unanswered(question: str, model_answer: str, status: str) -> None:
    """Append one row; existing rows are never rewritten or deleted."""
    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": _safe_cell(question),
        "model_answer": _safe_cell(model_answer),
        "status": status,
    }
    if review_sheet.is_configured():
        review_sheet.append_row([row[field] for field in FIELDS])
        logger.warning("Unanswered question appended to Google Sheets (status=%s)", status)
        return

    path = unanswered_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        is_new = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            if is_new:
                writer.writeheader()
            writer.writerow(row)
    logger.warning("Unanswered question appended to local review log (status=%s)", status)
