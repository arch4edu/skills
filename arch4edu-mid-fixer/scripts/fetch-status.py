#!/usr/bin/env python3
"""Fetch arch4edu build status from builds.json and categorize failures.

Usage:
    python3 fetch-status.py                          # Human-readable summary of FAILED
    python3 fetch-status.py --json                   # JSON output
    python3 fetch-status.py --category "Failed in build()"  # Filter by failure category
    python3 fetch-status.py --all                    # Show all statuses, not just FAILED
    python3 fetch-status.py --status SCHEDULED       # Filter by status
    python3 fetch-status.py --show-skipped           # Show skipped packages (aarch64, unsafe builder)
    python3 fetch-status.py --priority               # Show priority ranking by blocked downstream count
"""

import json
import os
import re
import sys
import urllib.request
from collections import defaultdict

# Import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import IGNORE_LIST

BUILDS_URL = "https://api.arch4edu.org/status/builds.json"
REPO_ROOT = os.path.expanduser("~/cactus_bot/repo")
MEMBERS_FILE = os.path.expanduser("~/.config/arch4edu/members.txt")

# Default arch4edu-related AUR usernames whose packages we skip.
# Override/extend by listing one username per line in MEMBERS_FILE.
DEFAULT_ARCH4EDU_MEMBERS = {
    "carlosal1015",
    "petronny",
}


def load_arch4edu_members():
    members = set(DEFAULT_ARCH4EDU_MEMBERS)
    try:
        with open(MEMBERS_FILE) as f:
            for line in f:
                u = line.strip()
                if u and not u.startswith("#"):
                    members.add(u)
    except FileNotFoundError:
        pass
    return members


ARCH4EDU_MEMBERS = load_arch4edu_members()

FAILURE_CATEGORIES = [
    "Missing dependencies",
    "Failed in check()",
    "Failed in gpg()",
    "Failed in sources()",
    "Failed in checksums()",
    "Failed in build()",
    "Failed in prepare()",
    "Failed in package()",
]


def fetch_builds():
    req = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "arch4edu-mid-fixer/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def is_aarch64(pkg):
    return pkg.get("key", "").startswith("aarch64/")


def is_unsafe_builder(pkg):
    key = pkg.get("key", "")
    cactus_path = os.path.join(REPO_ROOT, key, "cactus.yaml")
    if not os.path.isfile(cactus_path):
        return False
    try:
        with open(cactus_path) as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("group:"):
                    return "Unsafe" in stripped
        return False
    except (OSError, IOError):
        return False


def is_r_package(pkg):
    key = pkg.get("key", "")
    return "/r/" in key and key.startswith(("x86_64/r/", "aarch64/r/"))


def is_specialized_subsystem(pkg):
    """Packages under specialized subsystem trees we don't touch (ros2, rocm)."""
    key = pkg.get("key", "")
    return key.startswith(("x86_64/ros2/", "aarch64/ros2/", "x86_64/rocm/", "aarch64/rocm/"))


def aur_name_from_key(key):
    """Derive the likely AUR package name from a cactus repo key like 'x86_64/r/r-rlang'."""
    return key.rsplit("/", 1)[-1]


def batch_query_aur_maintainers(packages, batch_size=50):
    """Annotate each package with 'aur_maintainer' (str or None for orphan).

    Uses AUR RPC v5 batch info. Packages whose name can't be derived are left
    with aur_maintainer='unknown'. Network errors are swallowed — the skip
    filter is best-effort and should not break the script on transient failures.
    """
    name_to_pkgs = defaultdict(list)
    for p in packages:
        name = aur_name_from_key(p.get("key", ""))
        if name:
            name_to_pkgs[name].append(p)
        else:
            p["aur_maintainer"] = "unknown"

    names = list(name_to_pkgs.keys())
    for i in range(0, len(names), batch_size):
        chunk = names[i:i + batch_size]
        query = "&".join(f"arg[]={n}" for n in chunk)
        url = f"https://aur.archlinux.org/rpc/v5/info?{query}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "arch4edu-mid-fixer/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
        except Exception as e:
            print(f"warning: AUR RPC failed ({e}); maintainer skip filter disabled for this batch", file=sys.stderr)
            for n in chunk:
                for p in name_to_pkgs[n]:
                    p.setdefault("aur_maintainer", "unknown")
            continue

        found = {r["Name"]: r.get("Maintainer") for r in data.get("results", [])}
        for n in chunk:
            # AUR may return a different PackageBase; if the direct name misses,
            # we can't resolve without extra lookups — mark unknown.
            maint = found.get(n, "unknown")
            for p in name_to_pkgs[n]:
                p["aur_maintainer"] = maint


def is_orphan(pkg):
    return pkg.get("aur_maintainer") is None


def is_arch4edu_member(pkg):
    m = pkg.get("aur_maintainer")
    return isinstance(m, str) and m in ARCH4EDU_MEMBERS


def is_ignored(pkg):
    """Check if package is in the IGNORE_LIST."""
    return pkg.get("key", "") in IGNORE_LIST


def filter_eligible(packages):
    """First pass: local-only filters (no network)."""
    eligible = []
    skipped_aarch64 = []
    skipped_unsafe = []
    skipped_subsystem = []

    for p in packages:
        if is_aarch64(p):
            skipped_aarch64.append(p)
            continue
        if is_unsafe_builder(p):
            skipped_unsafe.append(p)
            continue
        if is_specialized_subsystem(p):
            skipped_subsystem.append(p)
            continue
        eligible.append(p)

    return eligible, skipped_aarch64, skipped_unsafe, skipped_subsystem


def filter_by_maintainer(packages):
    """Second pass: requires aur_maintainer annotation from batch_query_aur_maintainers."""
    eligible = []
    skipped_orphan = []
    skipped_member = []
    skipped_ignored = []

    for p in packages:
        if is_orphan(p):
            skipped_orphan.append(p)
            continue
        if is_arch4edu_member(p):
            skipped_member.append(p)
            continue
        if is_ignored(p):
            skipped_ignored.append(p)
            continue
        eligible.append(p)

    return eligible, skipped_orphan, skipped_member, skipped_ignored


def build_blocker_map(packages, eligible_keys):
    """Build reverse dependency map: for each package key, how many eligible packages are waiting on it."""
    blocks = defaultdict(list)
    for p in packages:
        detail = p.get("detail", "")
        m = re.search(r"Waiting for dependency: (\S+?)\.?$", detail)
        if m:
            dep = m.group(1)
            if p["key"] in eligible_keys:
                blocks[dep].append(p["key"])
    return blocks


def annotate_with_priority(packages, blocks):
    """Add blocks_count to each package based on the blocker map."""
    for p in packages:
        p["blocks_count"] = len(blocks.get(p["key"], []))
        p["blocks_packages"] = blocks.get(p["key"], [])


def categorize_packages(packages):
    categorized = {cat: [] for cat in FAILURE_CATEGORIES}
    categorized["Other"] = []

    for p in packages:
        if p["status"] != "FAILED":
            continue

        detail = p.get("detail", "")
        matched = False

        for cat in FAILURE_CATEGORIES:
            if cat in detail:
                if cat == "Failed in sources()" and not is_r_package(p):
                    continue
                categorized[cat].append(p)
                matched = True
                break

        if not matched:
            categorized["Other"].append(p)

    return categorized


def sort_by_priority(pkgs):
    return sorted(pkgs, key=lambda p: -p.get("blocks_count", 0))


def filter_by_status(packages, status):
    return [p for p in packages if p["status"] == status]


def fmt_pkg(p):
    bc = p.get("blocks_count", 0)
    maint = p.get("aur_maintainer") or "orphan"
    if maint == "unknown":
        maint = "?"
    detail = p.get("detail", "")[:90]
    prefix = f"  [{bc:3} blocked] " if bc > 0 else "  "
    return f"{prefix}{p['key']} @{maint}: {detail}"


def print_priority_view(categorized):
    all_failed = []
    for pkgs in categorized.values():
        all_failed.extend(pkgs)
    all_failed = sort_by_priority(all_failed)

    blockers = [p for p in all_failed if p.get("blocks_count", 0) > 0]
    non_blockers = [p for p in all_failed if p.get("blocks_count", 0) == 0]

    print(f"=== Priority Ranking (by downstream blockers) ===")
    print(f"Total FAILED: {len(all_failed)} | Blocking others: {len(blockers)} | No dependents: {len(non_blockers)}")

    if blockers:
        print(f"\n--- HIGH PRIORITY (blocking {sum(p['blocks_count'] for p in blockers)} packages) ---")
        for p in blockers:
            print(fmt_pkg(p))

    if non_blockers:
        print(f"\n--- LOW PRIORITY ({len(non_blockers)} packages, no downstream dependents) ---")
        for p in non_blockers[:15]:
            print(fmt_pkg(p))
        if len(non_blockers) > 15:
            print(f"  ... and {len(non_blockers) - 15} more")


def _print_skipped(title, pkgs):
    if not pkgs:
        return
    failed = [p for p in pkgs if p["status"] == "FAILED"]
    if not failed:
        return
    print(f"=== {title} ({len(failed)} FAILED) ===")
    for p in failed:
        maint = p.get("aur_maintainer") or "orphan"
        detail = p.get("detail", "")[:80]
        print(f"  {p['key']} @{maint}: {detail}")
    print()


def print_summary(categorized, packages, show_all, skipped_aarch64, skipped_unsafe,
                  skipped_subsystem, skipped_orphan, skipped_member, skipped_ignored, show_skipped):
    if show_all:
        statuses = {}
        for p in packages:
            s = p["status"]
            statuses[s] = statuses.get(s, 0) + 1
        print("=== Status Overview ===")
        for s, count in sorted(statuses.items(), key=lambda x: -x[1]):
            print(f"  {s}: {count}")
        print()

    if show_skipped:
        _print_skipped("Skipped: aarch64", skipped_aarch64)
        _print_skipped("Skipped: unsafe builder", skipped_unsafe)
        _print_skipped("Skipped: ros2/rocm subsystem", skipped_subsystem)
        _print_skipped("Skipped: AUR orphan", skipped_orphan)
        _print_skipped(f"Skipped: arch4edu member ({','.join(sorted(ARCH4EDU_MEMBERS))})", skipped_member)
        if skipped_ignored:
            failed = [p for p in skipped_ignored if p["status"] == "FAILED"]
            if failed:
                print(f"=== Skipped: ignored ({len(failed)} FAILED) ===")
                for p in failed:
                    reason = IGNORE_LIST.get(p["key"], "")
                    print(f"  {p['key']}: {reason}")
                print()

    failed_total = sum(len(v) for v in categorized.values())
    print(f"=== Failed Packages: {failed_total} total ===")
    for cat, pkgs in categorized.items():
        if not pkgs:
            continue
        pkgs_sorted = sort_by_priority(pkgs)
        print(f"\n{cat}: {len(pkgs_sorted)}")
        for p in pkgs_sorted[:20]:
            print(fmt_pkg(p))
        if len(pkgs_sorted) > 20:
            print(f"  ... and {len(pkgs_sorted) - 20} more")


def print_json(categorized, packages, show_all, skipped_aarch64, skipped_unsafe,
               skipped_subsystem, skipped_orphan, skipped_member, skipped_ignored, show_skipped):
    output = {"failed_categories": categorized, "arch4edu_members": sorted(ARCH4EDU_MEMBERS)}
    if show_all:
        statuses = {}
        for p in packages:
            s = p["status"]
            statuses.setdefault(s, []).append(p)
        output["all_statuses"] = {s: len(ps) for s, ps in statuses.items()}
    if show_skipped:
        output["skipped_aarch64"] = [p for p in skipped_aarch64 if p["status"] == "FAILED"]
        output["skipped_unsafe_builder"] = [p for p in skipped_unsafe if p["status"] == "FAILED"]
        output["skipped_subsystem"] = [p for p in skipped_subsystem if p["status"] == "FAILED"]
        output["skipped_orphan"] = [p for p in skipped_orphan if p["status"] == "FAILED"]
        output["skipped_arch4edu_member"] = [p for p in skipped_member if p["status"] == "FAILED"]
        output["skipped_ignored"] = [
            {"key": p["key"], "reason": IGNORE_LIST.get(p["key"], "")}
            for p in skipped_ignored if p["status"] == "FAILED"
        ]
    print(json.dumps(output, indent=2))


def main():
    data = fetch_builds()
    packages = data.get("packages", [])

    show_all = "--all" in sys.argv
    show_skipped = "--show-skipped" in sys.argv
    show_priority = "--priority" in sys.argv

    # Pass 1: local-only filters
    eligible, skipped_aarch64, skipped_unsafe, skipped_subsystem = filter_eligible(packages)

    # AUR lookup + pass 2: maintainer-based filters (orphan / arch4edu member)
    if "--status" not in sys.argv:
        batch_query_aur_maintainers(eligible)
        eligible, skipped_orphan, skipped_member, skipped_ignored = filter_by_maintainer(eligible)
    else:
        skipped_orphan, skipped_member, skipped_ignored = [], [], []

    eligible_keys = {p["key"] for p in eligible}
    blocks = build_blocker_map(packages, eligible_keys)
    annotate_with_priority(eligible, blocks)

    if "--status" in sys.argv:
        idx = sys.argv.index("--status") + 1
        if idx < len(sys.argv):
            status = sys.argv[idx]
            filtered = filter_by_status(eligible, status)
            print(f"=== {status}: {len(filtered)} packages ===")
            for p in sort_by_priority(filtered):
                print(fmt_pkg(p))
            return

    categorized = categorize_packages(eligible)

    if show_priority:
        print_priority_view(categorized)
        return

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
        print_json(categorized, packages, show_all, skipped_aarch64, skipped_unsafe,
                   skipped_subsystem, skipped_orphan, skipped_member, skipped_ignored, show_skipped)
    else:
        print_summary(categorized, packages, show_all, skipped_aarch64, skipped_unsafe,
                      skipped_subsystem, skipped_orphan, skipped_member, skipped_ignored, show_skipped)


if __name__ == "__main__":
    main()
