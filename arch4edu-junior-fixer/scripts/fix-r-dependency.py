#!/usr/bin/env python3
"""Analyze R packages that Failed in build() for missing dependency patterns.

Fetches build logs via `gh run view` when detail field lacks error info.
Handles Unicode curly quotes in R error messages.
Deps not in repo are routed to smart-add-package (AUR resolution).

Usage:
    python3 fix-r-build.py           # Human-readable
    python3 fix-r-build.py --json    # JSON output
"""

import re
import sys
from _common import (
    fetch_builds, get_failed, is_r_cran_package, check_dep_in_repo,
    fetch_build_log_deps, get_pkg_arch, print_json,
)

GUIDANCE_DIRECT = (
    "  Fix (direct): extract dep names from detail or build log\n"
    "  (dependency 'X' is not available), verify PUBLISHED,\n"
    "  add to cactus.yaml depends as x86_64/r/r-{name-lowercase}.\n"
    "  Do NOT use smart-add-package."
)

GUIDANCE_SMART_ADD = (
    "  Fix (smart-add): run smart-add-package on the FAILING package:\n"
    "    cd ~/cactus_bot/repo\n"
    "    python3 smart-add-package.py --nocheck -t template/<arch>-nocheck.yaml <pkg_key>\n"
    "  smart-add-package will resolve deps from AUR. Only depends/makedepends/\n"
    "  checkdepends changes are expected — revert any other changes."
)


def analyze(packages):
    pkg_keys = {p["key"]: p for p in packages}
    failed = get_failed(packages)

    fixable = []
    smart_add = []
    skipped = []

    for p in failed:
        detail = p.get("detail", "")
        pkg_key = p["key"]

        if not is_r_cran_package(p) or "Failed in build()" not in detail:
            continue

        pkg_arch = get_pkg_arch(p)

        # Try detail field first
        dep_matches = re.findall(r"dependency ['\u2018\u2019](\S+)['\u2019] is not available", detail)

        # Fall back to build log
        source = "detail"
        if not dep_matches:
            workflow_id = p.get("workflow", "")
            if workflow_id:
                dep_matches = fetch_build_log_deps(workflow_id)
                source = "build_log"

        if not dep_matches:
            skipped.append({
                "key": pkg_key,
                "reason": "No missing dep pattern in detail or build log",
            })
            continue

        fixable_deps = []
        all_found = True
        for dep in dep_matches:
            found_key = check_dep_in_repo(dep, pkg_arch, pkg_keys)
            if found_key:
                fixable_deps.append({"name": dep, "key": found_key})
            else:
                all_found = False
                break

        if all_found and fixable_deps:
            fixable.append({
                "key": pkg_key,
                "deps": fixable_deps,
                "source": source,
            })
        else:
            smart_add.append({
                "key": pkg_key,
                "deps": dep_matches,
                "source": source,
            })

    return {"fixable": fixable, "smart_add": smart_add, "skipped": skipped}


def print_summary(results):
    print("=== R Package Failed in build() Analysis ===")
    print(f"\nFixable (direct add): {len(results['fixable'])}")
    for item in results["fixable"]:
        dep_keys = [d["key"] for d in item["deps"]]
        print(f"  {item['key']} -> {dep_keys} (source: {item['source']})")
    if results["fixable"]:
        print(f"\n{GUIDANCE_DIRECT}")

    print(f"\nFixable (smart-add-package): {len(results['smart_add'])}")
    for item in results["smart_add"]:
        print(f"  {item['key']} -> {item['deps']} (source: {item['source']})")
    if results["smart_add"]:
        print(f"\n{GUIDANCE_SMART_ADD}")

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
