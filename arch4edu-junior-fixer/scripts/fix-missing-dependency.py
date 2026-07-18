#!/usr/bin/env python3
"""Analyze FAILED packages with Missing dependencies.

Checks each dep for: version constraints, repo presence, PUBLISHED status.
R packages with r- deps not in repo → smart-add-package.
Non-R x86_64 packages with leaf AUR deps (no AUR sub-deps) → smart-add-package.

Usage:
    python3 fix-missing-dependency.py           # Human-readable
    python3 fix-missing-dependency.py --json     # JSON output
"""

import subprocess
import sys
import urllib.request
import urllib.error
import json as _json

from _common import fetch_builds, get_failed, is_r_cran_package, check_dep_in_repo, get_pkg_arch, print_json

GUIDANCE_DIRECT = (
    "  Fix (direct): verify each dep is PUBLISHED in builds.json, use aur-cli\n"
    "  to confirm dep_type (None=depends, make=makedepends, check=checkdepends),\n"
    "  then add one line to cactus.yaml. Do NOT use smart-add-package."
)

GUIDANCE_SMART_ADD_R = (
    "  Fix (smart-add, R): run smart-add-package on the FAILING package:\n"
    "    cd ~/cactus_bot/repo\n"
    "    python3 smart-add-package.py --nocheck -t template/<arch>-nocheck.yaml <pkg_key>\n"
    "  All missing deps are r- packages. Only depends/makedepends/checkdepends\n"
    "  changes are expected — revert any other changes."
)

GUIDANCE_SMART_ADD_LEAF = (
    "  Fix (smart-add, leaf AUR): each missing dep is in AUR and has NO AUR\n"
    "  sub-dependencies (all its depends/makedepends are in official Arch repos).\n"
    "  Run smart-add-package on the FAILING package:\n"
    "    cd ~/cactus_bot/repo\n"
    "    python3 smart-add-package.py --nocheck -t template/<arch>-nocheck.yaml <pkg_key>\n"
    "  Only depends/makedepends/checkdepends changes expected — revert others."
)

_aur_cache = {}


_OFFICIAL_REPOS = {"core", "extra"}


def _is_in_official_repo(name):
    """Check if a package is in core or extra via expac."""
    try:
        r = subprocess.run(
            ["expac", "-S", "%r", name],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode != 0:
            return False
        return r.stdout.strip() in _OFFICIAL_REPOS
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_leaf_aur_package(dep_name):
    """Return True if dep_name is in AUR and all its depends/makedepends are
    in official Arch repos (i.e. it does not depend on other AUR packages).
    """
    if dep_name in _aur_cache:
        return _aur_cache[dep_name]

    try:
        url = f"https://aur.archlinux.org/rpc/v5/info/{dep_name}"
        req = urllib.request.Request(url, headers={"User-Agent": "arch4edu-junior-fixer/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.load(resp)
    except Exception:
        _aur_cache[dep_name] = False
        return False

    results = data.get("results", [])
    if not results:
        _aur_cache[dep_name] = False
        return False

    pkg = results[0]
    sub_deps = list(pkg.get("Depends", []) or []) + list(pkg.get("MakeDepends", []) or [])

    for sub_dep in sub_deps:
        if not _is_in_official_repo(sub_dep):
            _aur_cache[dep_name] = False
            return False

    _aur_cache[dep_name] = True
    return True


def analyze(packages):
    pkg_keys = {p["key"]: p for p in packages}
    failed = get_failed(packages)

    fixable = []
    smart_add_r = []
    smart_add_leaf = []
    skipped = []

    for p in failed:
        detail = p.get("detail", "")
        if "Missing dependencies:" not in detail:
            continue

        pkg_key = p["key"]
        pkg_arch = get_pkg_arch(p)
        is_r = is_r_cran_package(p)
        deps_str = detail.replace("Missing dependencies: ", "")
        deps = [d.strip() for d in deps_str.split(",")]

        if any(c in d for d in deps for c in "<>="):
            skipped.append({"key": pkg_key, "reason": "Version constraint required", "deps": deps})
            continue

        fixable_deps = []
        missing_deps = []
        for dep in deps:
            found_key = check_dep_in_repo(dep, pkg_arch, pkg_keys)
            if found_key:
                fixable_deps.append({"name": dep, "key": found_key})
            else:
                missing_deps.append(dep)

        if not missing_deps:
            fixable.append({"key": pkg_key, "deps": fixable_deps})
        elif is_r and all(d.startswith("r-") for d in missing_deps):
            smart_add_r.append({"key": pkg_key, "missing_deps": missing_deps})
        elif is_r:
            skipped.append({"key": pkg_key, "reason": f"Non-R deps not in repo: {', '.join(missing_deps)}", "deps": deps})
        elif pkg_arch == "x86_64" and all(is_leaf_aur_package(d) for d in missing_deps):
            smart_add_leaf.append({"key": pkg_key, "missing_deps": missing_deps})
        else:
            skipped.append({"key": pkg_key, "reason": "Dependencies not in repo", "deps": deps})

    return {
        "fixable": fixable,
        "smart_add_r": smart_add_r,
        "smart_add_leaf": smart_add_leaf,
        "skipped": skipped,
    }


def print_summary(results):
    print("=== Missing Dependencies Analysis ===")

    print(f"\nFixable (direct add): {len(results['fixable'])}")
    for item in results["fixable"]:
        dep_keys = [d["key"] for d in item["deps"]]
        print(f"  {item['key']} -> {dep_keys}")
    if results["fixable"]:
        print(f"\n{GUIDANCE_DIRECT}")

    print(f"\nFixable (smart-add, R packages): {len(results['smart_add_r'])}")
    for item in results["smart_add_r"]:
        print(f"  {item['key']} -> missing (not in repo): {item['missing_deps']}")
    if results["smart_add_r"]:
        print(f"\n{GUIDANCE_SMART_ADD_R}")

    print(f"\nFixable (smart-add, leaf AUR deps): {len(results['smart_add_leaf'])}")
    for item in results["smart_add_leaf"]:
        print(f"  {item['key']} -> leaf AUR (no AUR sub-deps): {item['missing_deps']}")
    if results["smart_add_leaf"]:
        print(f"\n{GUIDANCE_SMART_ADD_LEAF}")

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
