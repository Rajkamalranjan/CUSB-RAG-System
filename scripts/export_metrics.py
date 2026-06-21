"""Placeholder metrics export entrypoint."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    reports = sorted(Path("reports").glob("*.json"))
    summary = {"reports": [str(path) for path in reports]}
    Path("reports/metrics_export.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Wrote reports/metrics_export.json")


if __name__ == "__main__":
    main()

