#!/usr/bin/env python3
"""Analyze FAILED packages with Failed in checksums().

Checks AUR maintainer status. Skips packages maintained by arch4edu members
(petronny, carlosal1015, AutoUpdateBot).

Usage:
    python3 fix-checksums.py           # Human-readable
    python3 fix-checksums.py --json    # JSON output
"""

import json
import subprocess
import sys
from _common import fetch_builds, get_failed, print_json

ARCH4EDU_MEMBERS = {"petronny", "carlosal1015", "autoupdatebot"}

GUIDANCE = (
    "  Fix: download source, calc correct hash,\n"
    "  add `replace '<old>' '<new>'` to pre_build."
)


def _get_aur_maintainer(pkg_name):
    """Query AUR for maintainer info. Returns (maintainer, comaintainers) or None."""
    try:
        r = subprocess.run(
            ["aur-cli", "get-info", "--package", pkg_name, "--json"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return None
        data = json.loads(r.stdout)
        meta = data.get("metadata", {})
        maintainer = meta.get("maintainer", "") or meta.get("维护者", "")
        return maintainer.lower() if maintainer else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        return None


def _is_arch4edu_maintained(maintainer_str):
    """Check if any arch4edu member appears in the maintainer string."""
    if not maintainer_str:
        return False
    lower = maintainer_str.lower()
    return any(m in lower for m in ARCH4EDU_MEMBERS)


def analyze(packages):
    failed = get_failed(packages)
    fixable = []
    skipped = []
    for p in failed:
        if "Failed in checksums()" not in p.get("detail", ""):
            continue

        pkg_key = p["key"]
        pkg_name = pkg_key.rsplit("/", 1)[-1]

        maintainer = _get_aur_maintainer(pkg_name)
        if maintainer is None:
            skipped.append({"key": pkg_key, "reason": "aur-cli query failed"})
            continue

        if _is_arch4edu_maintained(maintainer):
            skipped.append({"key": pkg_key, "reason": f"Maintained by arch4edu member: {maintainer}"})
            continue

        fixable.append({"key": pkg_key, "maintainer": maintainer})

    return {"fixable": fixable, "skipped": skipped}


def print_summary(results):
    print("=== Failed in checksums() Analysis ===")
    print(f"\nFixable: {len(results['fixable'])}")
    for item in results["fixable"]:
        print(f"  {item['key']} (maintainer: {item['maintainer']})")
    if results["fixable"]:
        print(f"\n{GUIDANCE}")

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
