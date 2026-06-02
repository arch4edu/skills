#!/usr/bin/env python3
"""Analyze failed packages and determine which ones are fixable by the junior fixer.

Checks:
- Missing dependencies: deps must be in repo AND PUBLISHED, no version constraints
- R package missing deps (Failed in build()): extract from detail, check deps in repo
- Failed in check(): always fixable
- Failed in gpg(): always fixable
- Failed in sources(): only R CRAN packages with version updates available
- Failed in checksums(): skip if maintained by arch4edu members

Usage:
    python3 analyze-fixes.py              # Human-readable summary
    python3 analyze-fixes.py --json       # JSON output for programmatic use
"""

import json
import re
import sys
import urllib.request

BUILDS_URL = "https://api.arch4edu.org/status/builds.json"


def fetch_builds():
    req = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "arch4edu-junior-fixer/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def is_r_cran_package(pkg):
    key = pkg.get("key", "")
    return "/r/" in key and key.startswith(("x86_64/r/", "aarch64/r/"))


def check_dep_in_repo(dep, pkg_arch, pkg_keys):
    """Check if a dependency exists in repo and is PUBLISHED."""
    for arch in [pkg_arch, "any"]:
        for path_fmt in ["{arch}/{dep}", "{arch}/r/{dep}"]:
            dep_key = path_fmt.format(arch=arch, dep=dep)
            if dep_key in pkg_keys and pkg_keys[dep_key]["status"] == "PUBLISHED":
                return dep_key
    return None


def analyze_packages(packages):
    pkg_keys = {p["key"]: p for p in packages}
    failed = [p for p in packages if p["status"] == "FAILED"]

    results = {
        "fixable": {
            "Missing dependencies": [],
            "R package missing deps (Failed in build())": [],
            "Failed in check()": [],
            "Failed in gpg()": [],
            "Failed in sources()": [],
            "Failed in checksums()": [],
        },
        "skipped": [],
    }

    for p in failed:
        detail = p.get("detail", "")
        pkg_key = p["key"]
        pkg_arch = pkg_key.split("/")[0] if "/" in pkg_key else ""
        is_r = is_r_cran_package(p)

        # R packages with Failed in build() — check for missing dependency pattern
        if is_r and "Failed in build()" in detail:
            dep_matches = re.findall(r"dependency '(\S+)' is not available", detail)
            if dep_matches:
                fixable_deps = []
                all_found = True
                for dep in dep_matches:
                    found_key = check_dep_in_repo(dep, pkg_arch, pkg_keys)
                    if found_key:
                        fixable_deps.append(found_key)
                    else:
                        all_found = False
                        break

                if all_found and fixable_deps:
                    results["fixable"]["R package missing deps (Failed in build())"].append({
                        "key": pkg_key,
                        "deps": fixable_deps,
                        "detail": detail,
                    })
                else:
                    results["skipped"].append({
                        "key": pkg_key,
                        "category": "R package missing deps (Failed in build())",
                        "reason": f"Dependencies not in repo: {', '.join(dep_matches)}",
                        "detail": detail,
                    })
            else:
                results["skipped"].append({
                    "key": pkg_key,
                    "category": "Failed in build()",
                    "reason": "R package build failure not matching missing dep pattern",
                    "detail": detail,
                })
            continue

        if "Missing dependencies:" in detail:
            deps_str = detail.replace("Missing dependencies: ", "")
            deps = [d.strip() for d in deps_str.split(",")]

            if any("<" in d or ">" in d or "=" in d for d in deps):
                results["skipped"].append({
                    "key": pkg_key,
                    "category": "Missing dependencies",
                    "reason": "Version constraint required",
                    "detail": detail,
                })
                continue

            fixable_deps = []
            all_found = True
            for dep in deps:
                found_key = check_dep_in_repo(dep, pkg_arch, pkg_keys)
                if found_key:
                    fixable_deps.append(found_key)
                else:
                    all_found = False
                    break

            if all_found and fixable_deps:
                results["fixable"]["Missing dependencies"].append({
                    "key": pkg_key,
                    "deps": fixable_deps,
                    "detail": detail,
                })
            else:
                results["skipped"].append({
                    "key": pkg_key,
                    "category": "Missing dependencies",
                    "reason": "Dependencies not in repo",
                    "detail": detail,
                })

        elif "Failed in check()" in detail:
            results["fixable"]["Failed in check()"].append({"key": pkg_key, "detail": detail})

        elif "Failed in gpg()" in detail:
            results["fixable"]["Failed in gpg()"].append({"key": pkg_key, "detail": detail})

        elif "Failed in sources()" in detail:
            if not is_r:
                results["skipped"].append({
                    "key": pkg_key,
                    "category": "Failed in sources()",
                    "reason": "Not an R CRAN package",
                    "detail": detail,
                })
            else:
                results["fixable"]["Failed in sources()"].append({
                    "key": pkg_key,
                    "detail": detail,
                    "note": "Requires aur-cli to check for new version",
                })

        elif "Failed in checksums()" in detail:
            results["fixable"]["Failed in checksums()"].append({
                "key": pkg_key,
                "detail": detail,
                "note": "Requires aur-cli to verify maintainer",
            })

    return results


def print_summary(results):
    print("=== Junior Fix Analysis ===")
    print("\n--- Fixable ---")
    for cat, pkgs in results["fixable"].items():
        print(f"\n{cat}: {len(pkgs)}")
        for p in pkgs:
            deps = p.get("deps", [])
            note = p.get("note", "")
            dep_str = f" -> {deps}" if deps else ""
            note_str = f" ({note})" if note else ""
            print(f"  {p['key']}{dep_str}{note_str}")

    print(f"\n--- Skipped ({len(results['skipped'])}) ---")
    for s in results["skipped"][:20]:
        print(f"  {s['key']} ({s['category']}): {s['reason']}")
    if len(results["skipped"]) > 20:
        print(f"  ... and {len(results['skipped']) - 20} more")

    total_fixable = sum(len(v) for v in results["fixable"].values())
    print(f"\nTotal fixable: {total_fixable}")
    print(f"Total skipped: {len(results['skipped'])}")


def main():
    data = fetch_builds()
    packages = data.get("packages", [])
    results = analyze_packages(packages)

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))
    else:
        print_summary(results)


if __name__ == "__main__":
    main()
