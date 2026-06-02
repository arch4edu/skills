#!/usr/bin/env python3
"""Fetch FAILED packages from arch4edu builds.json and categorize by fixable type.

Usage:
    python3 fetch-failed.py              # Human-readable summary
    python3 fetch-failed.py --json       # JSON output for programmatic use
    python3 fetch-failed.py --category "Missing dependencies"  # Filter by category
"""

import json
import re
import sys
import urllib.request

BUILDS_URL = "https://api.arch4edu.org/status/builds.json"

FIXABLE_TYPES = [
    "Missing dependencies",
    "Failed in check()",
    "Failed in gpg()",
    "Failed in sources()",
    "Failed in checksums()",
]


def fetch_builds():
    req = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "arch4edu-junior-fixer/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def is_r_cran_package(pkg):
    """Check if a package is an R CRAN package based on its path."""
    key = pkg.get("key", "")
    return "/r/" in key and key.startswith(("x86_64/r/", "aarch64/r/"))


def categorize_packages(packages):
    failed = [p for p in packages if p["status"] == "FAILED"]

    categorized = {t: [] for t in FIXABLE_TYPES}
    categorized["R package missing deps (Failed in build())"] = []
    categorized["Other"] = []

    for p in failed:
        detail = p.get("detail", "")
        matched = False

        # Check R packages with Failed in build() for missing dependency pattern
        if is_r_cran_package(p) and "Failed in build()" in detail:
            dep_matches = re.findall(r"dependency '(\S+)' is not available", detail)
            if dep_matches:
                categorized["R package missing deps (Failed in build())"].append(p)
                matched = True

        if not matched:
            for t in FIXABLE_TYPES:
                if t in detail:
                    if t == "Failed in sources()" and not is_r_cran_package(p):
                        continue
                    categorized[t].append(p)
                    matched = True
                    break

        if not matched:
            categorized["Other"].append(p)

    return categorized


def print_summary(categorized):
    print("=== Failed Package Summary ===")
    for t, pkgs in categorized.items():
        print(f"\n{t}: {len(pkgs)}")
        for p in pkgs[:20]:
            print(f"  {p['key']}: {p.get('detail', '')[:100]}")
        if len(pkgs) > 20:
            print(f"  ... and {len(pkgs) - 20} more")


def print_json(categorized):
    print(json.dumps(categorized, indent=2))


def main():
    data = fetch_builds()
    packages = data.get("packages", [])
    categorized = categorize_packages(packages)

    if "--category" in sys.argv:
        idx = sys.argv.index("--category") + 1
        if idx < len(sys.argv):
            cat = sys.argv[idx]
            if cat in categorized:
                categorized = {cat: categorized[cat]}
            else:
                print(f"Unknown category: {cat}")
                print(f"Available: {', '.join(categorized.keys())}")
                sys.exit(1)

    if "--json" in sys.argv:
        print_json(categorized)
    else:
        print_summary(categorized)


if __name__ == "__main__":
    main()
