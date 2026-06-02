#!/usr/bin/env python3
"""Check if missing dependencies exist in the repo and are PUBLISHED.

Usage:
    python3 check-deps.py <pkg_key> [pkg_key2 ...]
    python3 check-deps.py --all
"""

import json
import sys
import urllib.request

BUILDS_URL = "https://api.arch4edu.org/status/builds.json"


def fetch_builds():
    req = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "arch4edu-junior-fixer/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def check_dep_in_repo(dep, pkg_arch, pkg_keys):
    for arch in [pkg_arch, "any"]:
        for path_fmt in ["{arch}/{dep}", "{arch}/r/{dep}"]:
            dep_key = path_fmt.format(arch=arch, dep=dep)
            if dep_key in pkg_keys:
                return dep_key, pkg_keys[dep_key]["status"]
    return None, None


def check_deps(pkg_key, packages):
    pkg_keys = {p["key"]: p for p in packages}
    pkg = None
    for p in packages:
        if p["key"] == pkg_key and p["status"] == "FAILED":
            pkg = p
            break

    if not pkg:
        print(f"{pkg_key}: Not found or not FAILED")
        return None

    detail = pkg.get("detail", "")
    if "Missing dependencies:" not in detail:
        print(f"{pkg_key}: Not a Missing dependencies failure")
        return None

    deps_str = detail.replace("Missing dependencies: ", "")
    deps = [d.strip() for d in deps_str.split(",")]
    pkg_arch = pkg_key.split("/")[0] if "/" in pkg_key else ""

    results = {"key": pkg_key, "deps": []}
    for dep in deps:
        has_constraint = any(c in dep for c in "<>=")
        dep_result = {"name": dep, "found": False, "status": None, "constraint": has_constraint}

        if has_constraint:
            dep_result["status"] = "SKIP (version constraint)"
            results["deps"].append(dep_result)
            continue

        dep_key, status = check_dep_in_repo(dep, pkg_arch, pkg_keys)
        if dep_key:
            dep_result["found"] = True
            dep_result["key"] = dep_key
            dep_result["status"] = status
        else:
            dep_result["status"] = "NOT IN REPO"

        results["deps"].append(dep_result)

    return results


def check_all(packages):
    failed = [p for p in packages if p["status"] == "FAILED" and "Missing dependencies:" in p.get("detail", "")]
    return [r for p in failed if (r := check_deps(p["key"], packages))]


def print_result(result):
    if isinstance(result, list):
        for r in result:
            print_result(r)
        return

    print(f"\n{result['key']}:")
    all_fixable = True
    for dep in result["deps"]:
        key_str = f" ({dep.get('key', '')})" if dep.get("key") else ""
        print(f"  {dep['name']}: {dep['status']}{key_str}")
        if dep["status"] != "PUBLISHED":
            all_fixable = False

    if all_fixable:
        print("  => FIXABLE")
    else:
        print("  => NOT FIXABLE")


def main():
    data = fetch_builds()
    packages = data.get("packages", [])

    if "--all" in sys.argv:
        print_result(check_all(packages))
    elif len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("-"):
                continue
            result = check_deps(arg, packages)
            if result:
                print_result(result)
    else:
        print("Usage: python3 check-deps.py <pkg_key> [...] or --all")
        sys.exit(1)


if __name__ == "__main__":
    main()
