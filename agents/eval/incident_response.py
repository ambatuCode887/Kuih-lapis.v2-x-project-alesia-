"""Offline, deterministic evaluation of the scam-victim incident playbook.

Runs ``build_incident_plan`` over ``datasets/incident_response_cases.csv`` and
reports detection quality, severity, step coverage and clarification behaviour.
No model, network or randomness is involved, so output is reproducible.

Metric definitions (denominators are always stated; ``None`` means the value is
undefined, never zero):

* TP / FP / FN / TN: a case is "positive" when ``expected_incident`` is true and
  "predicted" when a plan is returned.
* precision = TP / (TP + FP)            -- None if nothing was predicted.
* recall    = TP / (TP + FN)            -- None if there are no positives.
* f1        = 2PR / (P + R)             -- None if either is None or both are 0.
* false_positive_rate = FP / (FP + TN)  -- over legitimate negative cases.
* high_impact_false_negative_rate = missed / total, over positives whose
  ``expected_min_severity`` is "high" or "critical".
* category_accuracy: over true positives, the expected category is among the
  detected signal kinds.
* severity_in_range_rate: over true positives, severity is within the expected
  [min, max] range.
* required_step_coverage: over true positives, the mean fraction of required
  step ids present. A leading "!" means the step must also be unconditional.
* full_step_coverage_rate: over true positives, share with every required step.
* critical_full_step_coverage_rate: as above, restricted to high/critical cases.
* clarification_recall: over cases that expect a clarifying question, share
  where the plan asks at least one.

The dataset is synthetic and written by the developers, so results are
optimistic. ``split=tuned`` cases were all visible while the detection rules
were written, so scores on them measure coverage, not generalisation.
``split=challenge`` cases were written after the rules were frozen with
different phrasing and deliberate traps; they are the more honest estimate.
Report both, never tune on ``challenge``, and treat a perfect ``tuned`` score as
expected rather than impressive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from agents.tools.functions.incident import build_incident_plan
from agents.tools.functions.incident.playbook import SEVERITY_ORDER

_DATASET_PATH = Path(__file__).parent / "datasets" / "incident_response_cases.csv"
_DEFAULT_OUTPUT = Path(".artifacts/incident-response-report.json")

_COLUMNS = (
    "case_id",
    "split",
    "language",
    "user_request",
    "prior_incident",
    "assessment_level",
    "expected_incident",
    "expected_category",
    "expected_min_severity",
    "expected_max_severity",
    "required_steps",
    "clarification_expected",
    "review_status",
    "review_notes",
)
_SPLITS = {"tuned", "challenge"}
_LANGUAGES = {"en", "ms", "zh", "mixed"}
_ASSESSMENT_LEVELS = {"none", "low", "moderate", "high", "critical"}
_CATEGORIES = {
    "none",
    "money_sent",
    "financial_credentials",
    "other_credentials",
    "data_entered_on_site",
    "link_interaction",
    "remote_access",
    "app_installed",
    "identity_documents",
    "recovery_scam",
    "unspecified_victim",
}
_HIGH_IMPACT = {"high", "critical"}
_ASSESSMENT_CONFIDENCE = 85  # fixed so the dataset isolates risk level
_MAX_TEXT = 2000

PlanFn = Callable[..., Any]


def _bool(value: str) -> bool | None:
    value = (value or "").strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _step_tokens(raw: str) -> list[str]:
    return [token.strip() for token in (raw or "").split("|") if token.strip()]


def load_cases(path: str | Path = _DATASET_PATH) -> list[dict[str, str]]:
    """Load and strictly validate the dataset; raise ValueError listing every problem."""
    try:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = [column for column in _COLUMNS if column not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"dataset is missing columns: {', '.join(missing)}")
            rows = list(reader)
    except csv.Error as error:
        raise ValueError(f"dataset is not valid CSV: {error}") from error
    if not rows:
        raise ValueError("The incident-response dataset contains no cases.")

    errors: list[str] = []
    seen: set[str] = set()
    for line, row in enumerate(rows, start=2):
        label = f"line {line} ({row.get('case_id') or 'no id'})"
        if any(value is None for value in row.values()):
            errors.append(f"{label}: wrong number of columns")
            continue
        case_id = row["case_id"].strip()
        if not case_id:
            errors.append(f"{label}: empty case_id")
        elif case_id in seen:
            errors.append(f"{label}: duplicate case_id")
        seen.add(case_id)
        text = row["user_request"]
        if not text.strip() or len(text) > _MAX_TEXT:
            errors.append(f"{label}: user_request must be 1-{_MAX_TEXT} characters")
        if row["review_status"] != "reviewed":
            errors.append(f"{label}: review_status must be 'reviewed'")
        for column, allowed in (
            ("split", _SPLITS),
            ("language", _LANGUAGES),
            ("assessment_level", _ASSESSMENT_LEVELS),
            ("expected_category", _CATEGORIES),
        ):
            if row[column] not in allowed:
                errors.append(f"{label}: {column}={row[column]!r} not in {sorted(allowed)}")
        for column in ("prior_incident", "expected_incident", "clarification_expected"):
            if _bool(row[column]) is None:
                errors.append(f"{label}: {column} must be 'true' or 'false'")
        expected = _bool(row["expected_incident"])
        low, high = row["expected_min_severity"], row["expected_max_severity"]
        if expected is True:
            if row["expected_category"] == "none":
                errors.append(f"{label}: positive case needs an expected_category")
            if low not in SEVERITY_ORDER or high not in SEVERITY_ORDER:
                errors.append(f"{label}: severities must be one of {list(SEVERITY_ORDER)}")
            elif SEVERITY_ORDER.index(low) > SEVERITY_ORDER.index(high):
                errors.append(f"{label}: expected_min_severity is above expected_max_severity")
            if not _step_tokens(row["required_steps"]):
                errors.append(f"{label}: positive case needs required_steps")
        elif expected is False:
            if row["expected_category"] != "none" or low or high or row["required_steps"].strip():
                errors.append(f"{label}: negative case must not set category, severity or steps")
        for token in _step_tokens(row["required_steps"]):
            step_id = token.lstrip("!")
            if not step_id.replace("_", "").isalnum() or not step_id.islower():
                errors.append(f"{label}: invalid step id {token!r}")
    if errors:
        raise ValueError("Invalid incident-response dataset:\n- " + "\n- ".join(errors))
    return rows


def _assessment(level: str) -> Mapping[str, Any] | None:
    if level == "none":
        return None
    return {"risk_level": level, "confidence": _ASSESSMENT_CONFIDENCE}


def evaluate_case(case: Mapping[str, str], plan_fn: PlanFn = build_incident_plan) -> dict[str, Any]:
    """Score one case. Playbook exceptions are reported as errors, never swallowed."""
    expected = _bool(case["expected_incident"]) is True
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "split": case["split"],
        "language": case["language"],
        "expected_incident": expected,
        "expected_category": case["expected_category"],
        "error": None,
    }
    try:
        plan = plan_fn(
            case["user_request"],
            _assessment(case["assessment_level"]),
            prior_incident=_bool(case["prior_incident"]) is True,
        )
    except Exception as error:  # noqa: BLE001 - surfaced in the report
        result.update(predicted=False, error=f"{type(error).__name__}: {error}")
        return result

    predicted = plan is not None
    result["predicted"] = predicted
    if not predicted:
        return result

    kinds = {signal.kind for signal in plan.signals}
    steps = {step.id: step for step in plan.steps}
    result["detected_categories"] = sorted(kinds)
    result["severity"] = plan.severity
    if not expected:
        return result

    low = SEVERITY_ORDER.index(case["expected_min_severity"])
    high = SEVERITY_ORDER.index(case["expected_max_severity"])
    required = _step_tokens(case["required_steps"])
    present = []
    for token in required:
        step = steps.get(token.lstrip("!"))
        present.append(step is not None and not (token.startswith("!") and step.conditional))
    result.update(
        category_match=case["expected_category"] in kinds,
        severity_in_range=low <= SEVERITY_ORDER.index(plan.severity) <= high,
        missing_steps=[token for token, ok in zip(required, present) if not ok],
        step_coverage=sum(present) / len(required),
        asks_question=bool(plan.questions),
    )
    return result


def _ratio(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _detection_metrics(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [row for row in results if not row.get("error")]
    tp = sum(1 for r in rows if r["expected_incident"] and r["predicted"])
    fp = sum(1 for r in rows if not r["expected_incident"] and r["predicted"])
    fn = sum(1 for r in rows if r["expected_incident"] and not r["predicted"])
    tn = sum(1 for r in rows if not r["expected_incident"] and not r["predicted"])
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    f1 = (
        round(2 * precision * recall / (precision + recall), 4)
        if precision is not None and recall is not None and (precision + recall) > 0
        else None
    )
    return {
        "cases": len(rows),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": _ratio(fp, fp + tn),
    }


def summarize_results(
    results: list[Mapping[str, Any]], cases: list[Mapping[str, str]]
) -> dict[str, Any]:
    """Aggregate metrics overall and by split, language and category."""
    by_id = {case["case_id"]: case for case in cases}
    tp_rows = [r for r in results if not r.get("error") and r["expected_incident"] and r["predicted"]]
    positives = [r for r in results if not r.get("error") and r["expected_incident"]]
    high_impact = [
        r for r in positives if by_id[r["case_id"]]["expected_min_severity"] in _HIGH_IMPACT
    ]
    critical_tp = [r for r in tp_rows if r in high_impact]
    clar = [r for r in tp_rows if _bool(by_id[r["case_id"]]["clarification_expected"])]

    groups: dict[str, dict[str, list[Mapping[str, Any]]]] = {
        "by_split": defaultdict(list),
        "by_language": defaultdict(list),
        "by_category": defaultdict(list),
    }
    for row in results:
        groups["by_split"][row["split"]].append(row)
        groups["by_language"][row["language"]].append(row)
        # Negatives are grouped under "none" so false positives stay visible.
        groups["by_category"][row["expected_category"]].append(row)

    def category_block(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
        block = _detection_metrics(rows)
        pos = [r for r in rows if not r.get("error") and r["expected_incident"] and r["predicted"]]
        block["category_accuracy"] = _ratio(sum(r["category_match"] for r in pos), len(pos))
        block["severity_in_range_rate"] = _ratio(sum(r["severity_in_range"] for r in pos), len(pos))
        return block

    return {
        "case_count": len(results),
        "error_count": sum(1 for r in results if r.get("error")),
        "overall": _detection_metrics(results),
        "high_impact_false_negative_rate": _ratio(
            sum(1 for r in high_impact if not r["predicted"]), len(high_impact)
        ),
        "high_impact_cases": len(high_impact),
        "category_accuracy": _ratio(sum(r["category_match"] for r in tp_rows), len(tp_rows)),
        "severity_in_range_rate": _ratio(sum(r["severity_in_range"] for r in tp_rows), len(tp_rows)),
        "required_step_coverage": _ratio(sum(r["step_coverage"] for r in tp_rows), len(tp_rows)),
        "full_step_coverage_rate": _ratio(
            sum(1 for r in tp_rows if not r["missing_steps"]), len(tp_rows)
        ),
        "critical_full_step_coverage_rate": _ratio(
            sum(1 for r in critical_tp if not r["missing_steps"]), len(critical_tp)
        ),
        "clarification_recall": _ratio(sum(r["asks_question"] for r in clar), len(clar)),
        "by_split": {k: _detection_metrics(v) for k, v in sorted(groups["by_split"].items())},
        "by_language": {k: _detection_metrics(v) for k, v in sorted(groups["by_language"].items())},
        "by_category": {k: category_block(v) for k, v in sorted(groups["by_category"].items())},
    }


def run_evaluation(
    path: str | Path = _DATASET_PATH, plan_fn: PlanFn = build_incident_plan
) -> dict[str, Any]:
    cases = load_cases(path)
    results = [evaluate_case(case, plan_fn) for case in cases]
    digest = hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return {
        "dataset": Path(path).name,
        "dataset_sha256": digest,
        "summary": summarize_results(results, cases),
        "failures": [
            {key: row[key] for key in row if key not in {"expected_incident"}}
            for row in results
            if row.get("error")
            or row["expected_incident"] != row["predicted"]
            or (row["expected_incident"] and (
                not row["category_match"]
                or not row["severity_in_range"]
                or row["missing_steps"]
            ))
        ],
        "results": results,
    }


def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the incident-response playbook.")
    parser.add_argument("--dataset", default=str(_DATASET_PATH))
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
    args = parser.parse_args()
    try:
        report = run_evaluation(args.dataset)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = report["summary"]
    overall = summary["overall"]
    print(f"cases={summary['case_count']} errors={summary['error_count']}")
    print(
        "detection: precision={} recall={} f1={} false_positive_rate={}".format(
            *(_fmt(overall[k]) for k in ("precision", "recall", "f1", "false_positive_rate"))
        )
    )
    for key in (
        "high_impact_false_negative_rate",
        "category_accuracy",
        "severity_in_range_rate",
        "required_step_coverage",
        "critical_full_step_coverage_rate",
        "clarification_recall",
    ):
        print(f"{key}: {_fmt(summary[key])}")
    for split, block in summary["by_split"].items():
        print(f"split {split}: recall={_fmt(block['recall'])} precision={_fmt(block['precision'])} "
              f"fpr={_fmt(block['false_positive_rate'])} (n={block['cases']})")
    print(f"failures: {len(report['failures'])} (see {output})")
    return 1 if summary["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
