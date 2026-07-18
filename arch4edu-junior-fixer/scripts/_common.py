"""Shared utilities for arch4edu-junior-fixer scripts."""

import json
import re
import subprocess
import urllib.request

BUILDS_URL = "https://api.arch4edu.org/status/builds.json"


def fetch_builds():
    req = urllib.request.Request(BUILDS_URL, headers={"User-Agent": "arch4edu-junior-fixer/1.0"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def get_failed(packages):
    return [p for p in packages if p["status"] == "FAILED"]


def is_r_cran_package(pkg):
    key = pkg.get("key", "")
    return "/r/" in key and key.startswith(("x86_64/r/", "aarch64/r/"))


def check_dep_in_repo(dep, pkg_arch, pkg_keys):
    """Check if a dependency exists in repo and is PUBLISHED.
    Tries {arch}/{dep}, {arch}/r/{dep}, {arch}/r/r-{dep-lowercase}.
    """
    for arch in [pkg_arch, "any"]:
        for path_fmt in ["{arch}/{dep}", "{arch}/r/{dep}", "{arch}/r/r-{dep}"]:
            dep_key = path_fmt.format(arch=arch, dep=dep.lower())
            if dep_key in pkg_keys and pkg_keys[dep_key]["status"] == "PUBLISHED":
                return dep_key
    return None


def fetch_build_log_deps(workflow_id):
    """Fetch GitHub Actions build log and extract missing R dependency names.
    Handles both ASCII straight quotes and Unicode curly quotes.
    """
    try:
        result = subprocess.run(
            ["gh", "run", "view", str(workflow_id), "--repo", "arch4edu/cactus", "--log"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return None
        return re.findall(
            r"dependency [''\u2018\u2019](\S+)[''\u2018\u2019] is not available",
            result.stdout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_pkg_arch(pkg):
    key = pkg.get("key", "")
    return key.split("/")[0] if "/" in key else ""


def print_json(data):
    print(json.dumps(data, indent=2))
