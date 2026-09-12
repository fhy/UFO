#!/usr/bin/env python3
"""Safely replace the published TikTok report after backing up the old copy."""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
REPORT = BASE / "report.json"
BACKUPS = BASE.parents[1] / ".cache" / "tiktok_report_backups"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="JSON file containing the new report")
    args = parser.parse_args()

    with args.source.open(encoding="utf-8") as stream:
        new_report = json.load(stream)
    if not isinstance(new_report, dict) or not isinstance(
        new_report.get("products"), list
    ):
        raise ValueError("report must be an object with a products array")

    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(REPORT, BACKUPS / f"report-{stamp}.json")

    temporary = REPORT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(new_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(REPORT)
    print(f"Backed up previous report and updated {REPORT}")


if __name__ == "__main__":
    main()
