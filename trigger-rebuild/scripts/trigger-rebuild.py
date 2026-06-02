#!/usr/bin/env python3
"""Trigger a rebuild for a package in arch4edu/cactus.

First tries gh run rerun (within 90-day retention).
Falls back to trigger_js.yml workflow dispatch.

Usage:
    python3 trigger-rebuild.py <full-path>

Requires full path:
    x86_64/r/r-rlang, aarch64/flutter, any/python-tokenizers
Short names are NOT accepted.
"""

import json
import subprocess
import sys
import urllib.request

BUILDS_URL = "https://api.arch4edu.org/status/builds.json"
REPO = "arch4edu/cactus"


def fetch_builds():
    req = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "trigger-rebuild/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def find_package(name, packages):
    """Find a package by its full path key."""
    for p in packages:
        if p["key"] == name:
            return p
    return None


def run_cmd(cmd):
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def trigger_rerun(workflow_id):
    """Try gh run rerun."""
    if not workflow_id:
        return False, "No workflow ID"

    cmd = f"gh run rerun {workflow_id} --repo {REPO}"
    success, output = run_cmd(cmd)
    return success, output


def trigger_workflow(pkg_key):
    """Fallback: trigger trigger_js.yml workflow."""
    cmd = f"gh workflow run trigger_js.yml --repo {REPO} --field pkgbase={pkg_key}"
    success, output = run_cmd(cmd)
    return success, output


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 trigger-rebuild.py <full-path>")
        print("  Requires full path: x86_64/r/r-rlang, aarch64/flutter, any/python-tokenizers")
        print("  Short names (e.g. r-rlang) are NOT accepted.")
        sys.exit(1)

    name = sys.argv[1]

    if "/" not in name:
        print(f"Error: '{name}' is not a valid full path.")
        print("  Requires full path: x86_64/r/r-rlang, aarch64/flutter, any/python-tokenizers")
        sys.exit(1)

    data = fetch_builds()
    packages = data.get("packages", [])

    pkg = find_package(name, packages)

    if not pkg:
        print(f"Package not found: {name}")
        sys.exit(1)

    pkg_key = pkg["key"]
    workflow_id = pkg.get("workflow")

    print(f"Looking up {pkg_key}...")
    print(f"  Found: {pkg_key} (status={pkg['status']}, workflow={workflow_id})")

    # Try rerun first
    print(f"Attempting gh run rerun {workflow_id}...")
    success, output = trigger_rerun(workflow_id)
    if success:
        print(f"OK Rerun triggered: {workflow_id}")
        print(f"Monitor: gh run view {workflow_id} --repo {REPO}")
        return

    # Fallback to workflow dispatch
    print(f"Rerun failed, falling back to trigger_js.yml...")
    success, output = trigger_workflow(pkg_key)
    if success:
        print(f"OK Workflow triggered: {pkg_key}")
        print(f"Package marked STALE, build system will auto-schedule.")
    else:
        print(f"FAILED: {output}")
        sys.exit(1)


if __name__ == "__main__":
    main()
