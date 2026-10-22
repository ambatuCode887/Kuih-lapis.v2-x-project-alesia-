"""Compare ruff and pyright findings for agents/ and tests/ against lint-baseline.json.

Fails when the count for any (tool, file, rule) rises above the recorded baseline.
Run with --update after intentionally accepting or fixing findings.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "lint-baseline.json"
TARGETS = ["agents", "tests"]


def _run(module: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _relative(path: str) -> str:
    return Path(path).resolve().relative_to(ROOT).as_posix()


def collect() -> Counter[str]:
    counts: Counter[str] = Counter()

    ruff = _run("ruff", ["check", *TARGETS, "--output-format", "json", "--exit-zero"])
    if ruff.returncode != 0:
        sys.exit(f"ruff failed to run:\n{ruff.stderr}")
    for item in json.loads(ruff.stdout or "[]"):
        counts[f"ruff|{_relative(item['filename'])}|{item['code']}"] += 1

    pyright = _run("pyright", ["--outputjson"])
    if pyright.returncode not in (0, 1) or "{" not in pyright.stdout:
        sys.exit(f"pyright failed to run:\n{pyright.stderr or pyright.stdout}")
    payload = json.loads(pyright.stdout[pyright.stdout.index("{") :])
    for diag in payload["generalDiagnostics"]:
        if diag["severity"] != "information":
            rule = diag.get("rule", "unknown")
            counts[f"pyright|{_relative(diag['file'])}|{rule}"] += 1

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true", help="rewrite lint-baseline.json from current findings")
    args = parser.parse_args()

    current = collect()

    if args.update:
        BASELINE.write_text(json.dumps(dict(sorted(current.items())), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {sum(current.values())} findings to {BASELINE.name}")
        return 0

    if not BASELINE.exists():
        sys.exit(f"{BASELINE.name} not found; run: python scripts/lint_baseline.py --update")

    baseline: Counter[str] = Counter(json.loads(BASELINE.read_text(encoding="utf-8")))
    regressions = {
        key: (baseline.get(key, 0), count)
        for key, count in current.items()
        if count > baseline.get(key, 0)
    }

    if regressions:
        print("New findings above baseline:")
        for key, (before, now) in sorted(regressions.items()):
            print(f"  {key}: {before} -> {now}")
        print("Fix them, or run with --update if the change is intentional.")
        return 1

    fewer = sum((baseline - current).values())
    print(f"No new findings. {sum(current.values())} recorded, {fewer} fewer than baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
