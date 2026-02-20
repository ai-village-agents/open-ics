#!/usr/bin/env python3
"""Enhance open-ics JSON report with metadata.

This script is used by the .github/actions/ics-lint composite action.
It intentionally lives as a real file to avoid YAML parsing issues caused
by embedding unindented Python in a YAML heredoc.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any


def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def main() -> int:
    p = argparse.ArgumentParser(description="Enhance open-ics JSON report with metadata")
    p.add_argument("--raw", default="/tmp/raw_report.json", help="Path to raw open-ics --json output")
    p.add_argument("--out", default="open_ics_report.json", help="Output path for enhanced report")
    args = p.parse_args()

    raw = _load_json(args.raw)

    enhanced = {
        "files_scanned": int(os.environ.get("FILES_SCANNED", "0") or 0),
        "tool_versions": {
            "python": os.environ.get("PYTHON_VERSION", "unknown"),
            "open_ics": os.environ.get("OPEN_ICS_VERSION", "unknown"),
        },
        "results": raw,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(enhanced, f, indent=2)
        f.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
