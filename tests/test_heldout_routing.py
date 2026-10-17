from __future__ import annotations

import csv
import re
from pathlib import Path

import httpx
import pytest

from agents.agent import route_request_to_agent
from agents.config import env
from agents.tools.functions.semantic_route import _EXEMPLARS

DATASETS = Path(__file__).resolve().parents[1] / "agents" / "eval" / "datasets"
HELDOUT_PATH = DATASETS / "routing_heldout.csv"
DEV_PATH = DATASETS / "routing_cases.csv"

# Known misses are kept visible as strict xfails; fixing them must not tune the held-out set.
KNOWN_MISSES: dict[str, str] = {}


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def _load(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _reachable(url: str) -> bool:
    try:
        httpx.get(url, timeout=2.0)
    except httpx.HTTPError:
        return False
    return True


OLLAMA_UP = _reachable(env("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/api/tags")
HELDOUT_ROWS = _load(HELDOUT_PATH)


def test_heldout_routing_cases_do_not_overlap_dev_or_exemplars() -> None:
    seen = {_normalize(row["request"]) for row in _load(DEV_PATH)}
    seen |= {_normalize(text) for texts in _EXEMPLARS.values() for text in texts}

    overlaps = [row["id"] for row in HELDOUT_ROWS if _normalize(row["request"]) in seen]

    assert not overlaps, f"held-out cases leak into dev or exemplars: {overlaps}"


def test_heldout_routing_set_covers_both_routes() -> None:
    routes = [row["expected_route"] for row in HELDOUT_ROWS]

    assert routes.count("retrieval_agent") >= 10
    assert routes.count("message_agent") >= 10


@pytest.mark.skipif(not OLLAMA_UP, reason="Ollama must be running for semantic routing.")
@pytest.mark.parametrize(
    "row",
    [
        pytest.param(
            row,
            id=row["id"],
            marks=pytest.mark.xfail(strict=True, reason=KNOWN_MISSES[row["id"]])
            if row["id"] in KNOWN_MISSES
            else (),
        )
        for row in HELDOUT_ROWS
    ],
)
def test_heldout_routing_case(row: dict[str, str]) -> None:
    actual = route_request_to_agent(
        row["request"],
        attachment_present=row["has_attachment"].casefold() == "true",
    )

    assert actual == row["expected_route"], row["request"]
