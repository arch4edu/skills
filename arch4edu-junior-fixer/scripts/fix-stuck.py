#!/usr/bin/env python3
"""Detect packages stuck in SCHEDULED or BUILDING status.

Thresholds:
  - SCHEDULED > 1 hour
  - BUILDING > 6 hours

Usage:
    python3 fix-stuck.py           # Human-readable
    python3 fix-stuck.py --json    # JSON output
"""

import sys
import time
from _common import fetch_builds, print_json

SCHEDULED_THRESHOLD_H = 1
BUILDING_THRESHOLD_H = 6

GUIDANCE = (
    "  Fix: trigger rebuild with:\n"
    "    python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <key>"
)


def analyze(packages, generated_at):
    now = generated_at or int(time.time())
    stuck = []
    for p in packages:
        status = p.get("status", "")
        ts = p.get("timestamp", 0)
        if not ts:
            continue
        age_h = (now - ts) / 3600
        if status == "SCHEDULED" and age_h > SCHEDULED_THRESHOLD_H:
            stuck.append({"key": p["key"], "status": status, "age_hours": round(age_h, 1)})
        elif status == "BUILDING" and age_h > BUILDING_THRESHOLD_H:
            stuck.append({"key": p["key"], "status": status, "age_hours": round(age_h, 1)})
    stuck.sort(key=lambda x: -x["age_hours"])
    return {"stuck": stuck}


def print_summary(results):
    print("=== Stuck Packages (SCHEDULED/BUILDING) ===")
    print(f"\nStuck: {len(results['stuck'])}")
    for item in results["stuck"]:
        print(f"  {item['key']}  [{item['status']}] {item['age_hours']}h")
    if results["stuck"]:
        print(f"\n{GUIDANCE}")


def main():
    data = fetch_builds()
    packages = data.get("packages", [])
    generated_at = data.get("generated_at")
    results = analyze(packages, generated_at)

    if "--json" in sys.argv:
        print_json(results)
    else:
        print_summary(results)


if __name__ == "__main__":
    main()
