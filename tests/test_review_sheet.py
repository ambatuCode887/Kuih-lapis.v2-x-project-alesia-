import pytest
from google.auth.exceptions import RefreshError

from agents.tools.functions import review_sheet


def test_auth_failure_surfaces_as_sheet_error(monkeypatch):
    def fail_auth():
        raise RefreshError("token refresh failed")

    monkeypatch.setattr(review_sheet, "_auth_headers", fail_auth)

    with pytest.raises(review_sheet.ReviewSheetError, match="auth failed"):
        review_sheet.append_row(["2026-01-01T00:00:00+00:00", "q", "a", "pending_review"])


def test_sheet_error_is_oserror_so_retrieval_logs_and_continues():
    assert issubclass(review_sheet.ReviewSheetError, OSError)
