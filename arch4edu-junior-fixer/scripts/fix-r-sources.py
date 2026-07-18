#!/usr/bin/env python3
"""Analyze FAILED packages with Failed in sources() — R CRAN packages only.

Non-R packages are skipped. R CRAN packages need aur-cli to check for
new versions or CRAN Archive availability.

Usage:
    python3 fix-sources.py           # Human-readable
    python3 fix-sources.py --json    # JSON output
"""

import sys
from _common import fetch_builds, get_failed, is_r_cran_package, print_json

GUIDANCE = (
    "  Fix (R CRAN only): aur-cli get-info to find new version.\n"
    "  New version: add `replace -u '<old>' '<new>'` to pre_build.\n"
    "  Archived: add `replace 'src/contrib/' 'src/contrib/Archive/<pkg>/'` to pre_build.\n"
    "  Skip non-R packages."
)


def analyze(packages):
    failed = get_failed(packages)
    fixable = []
    skipped = []

    for p in failed:
        if "Failed in sources()" not in p.get("detail", ""):
            continue

        if is_r_cran_package(p):
            fixable.append({"key": p["key"], "note": "Requires aur-cli to check for new version"})
        else:
            skipped.append({"key": p["key"], "reason": "Not an R CRAN package"})

    return {"fixable": fixable, "skipped": skipped}


def print_summary(results):
    print("=== Failed in sources() Analysis ===")
    print(f"\nFixable (R CRAN): {len(results['fixable'])}")
    for item in results["fixable"]:
        print(f"  {item['key']} ({item['note']})")
    if results["fixable"]:
        print(f"\n{GUIDANCE}")

    if results["skipped"]:
        print(f"\nSkipped: {len(results['skipped'])}")
        for item in results["skipped"]:
            print(f"  {item['key']}: {item['reason']}")


def main():
    data = fetch_builds()
    packages = data.get("packages", [])
    results = analyze(packages)

    if "--json" in sys.argv:
        print_json(results)
    else:
        print_summary(results)


if __name__ == "__main__":
    main()
