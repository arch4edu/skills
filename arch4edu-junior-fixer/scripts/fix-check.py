#!/usr/bin/env python3
"""Analyze FAILED packages with Failed in check().

All such failures are fixable by adding --nocheck to makepkg_args.

Usage:
    python3 fix-check.py           # Human-readable
    python3 fix-check.py --json    # JSON output
"""

import sys
from _common import fetch_builds, get_failed, print_json

GUIDANCE = (
    "  Fix: add `makepkg_args: --nocheck` to cactus.yaml.\n"
    "  If makepkg_args already exists, append --nocheck."
)


def analyze(packages):
    failed = get_failed(packages)
    fixable = []
    for p in failed:
        if "Failed in check()" in p.get("detail", ""):
            fixable.append({"key": p["key"]})
    return {"fixable": fixable}


def print_summary(results):
    print("=== Failed in check() Analysis ===")
    print(f"\nFixable: {len(results['fixable'])}")
    for item in results["fixable"]:
        print(f"  {item['key']}")
    if results["fixable"]:
        print(f"\n{GUIDANCE}")


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
