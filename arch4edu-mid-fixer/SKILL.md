---
name: arch4edu-mid-fixer
description: Mid-level arch4edu build failure fixer. Fetches builds.json status, categorizes failures by two-tier priority (any/ first, then package() failures), and provides a 7-step fix workflow (AUR clone → smart-build reproduce → PKGBUILD fix → cactus.yaml → simulate pre_build → commit/push → trigger-rebuild). Handles x86_64 and any packages on standard builders only.
---

# Arch4edu Mid Fixer

## Overview

Mid-level automated analysis and fix for arch4edu build failures. Fetches build status from the API, categorizes failures, and provides structured diagnostics. Designed for medium-difficulty packaging issues that go beyond simple dependency additions or flag toggling. Only handles x86_64 and any architecture packages on standard builders.

## One Package At A Time

**MUST**: Work on only ONE package at a time. Do not start working on another package until the current one is:
- Successfully committed, pushed, and rebuild triggered, OR
- Explicitly abandoned by the user

When abandoning a package:
1. Add to `config.py` IGNORE_LIST with a **short reason** (e.g., "requires source patches")
2. **Record detailed attempt process in memory** using `memory_add` — include what was tried, why it failed, and why it was abandoned. This helps future reference and avoids duplicate attempts.

This ensures focus and prevents partial/incomplete fixes.

## MANDATORY: Skill-Only Operations

These operations **MUST** use the designated skill/script. Manual alternatives (`gh workflow run`, raw `curl`, etc.) are **FORBIDDEN**:

| Operation | Required command | NEVER use |
|-----------|-----------------|-----------|
| Trigger rebuild | `python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <path>` | `gh workflow run "Trigger rebuild"` |
| Query AUR info | `~/bin/aur-cli get-info --package <name>` | Web scraping, raw AUR RPC |
| Build package | `smart-x86_64-build` (from `smart-build` skill) | Raw `makepkg`, `extra-x86_64-build` |
| Monitor build | `build-monitor` (from `qoderwake-monitor` skill) | Manual `sleep` + `grep` polling |

If you catch yourself typing a manual alternative, **STOP** and use the skill instead.

## Skip Rules (Hard Filters)

These packages are automatically excluded from analysis and fixing:

1. **aarch64 packages** — All packages with `key` starting with `aarch64/` are skipped. This skill only handles `x86_64/` and `any/` packages.
2. **Unsafe builder packages** — Packages with `group: GitHubActionsUnsafe` in their `cactus.yaml` are skipped. These use a different build environment and require separate handling.
3. **Failed in download()** — Source download failures. Handled by retry or manual intervention, not a packaging fix.
4. **Missing dependencies** — Dependency resolution failures. Handled by `arch4edu-junior-fixer` or `smart-add-package`.
5. **Failed in check()** — Test failures. Handled by `arch4edu-junior-fixer` (typically `makepkg_args: --nocheck`).
6. **Failed in checksums()** — Checksum mismatches. Handled by `arch4edu-junior-fixer` (typically `updpkgsums`).
7. **Failed in gpg()** — GPG signature issues. Handled by `arch4edu-junior-fixer` (typically `recv-gpg-keys`).
8. **Failed in sources() (R CRAN)** — R CRAN package source 404 failures (path contains `/r/`). Handled by `arch4edu-junior-fixer`.
9. **arch4edu member packages** — The script batch-queries AUR RPC for the `Maintainer` field of every eligible package and skips any whose AUR maintainer is a known arch4edu team member. The default member list is hardcoded (`carlosal1015`, `petronny`); extend it by listing one username per line in `~/.config/arch4edu/members.txt`. Note: AUR RPC does **not** expose Co-Maintainers, so co-maintainer-only ownership is not caught.
10. **ros2/rocm subsystem packages** — Packages whose cactus key starts with `x86_64/ros2/`, `aarch64/ros2/`, `x86_64/rocm/`, or `aarch64/rocm/`. These require specialized build environments and domain knowledge outside the scope of this skill.
11. **AUR orphan packages** — Packages whose AUR `Maintainer` field is `null` (i.e. orphaned on AUR). Detected via the same batch RPC call as rule 9.

Use `--show-skipped` to see which packages were filtered out.

## Usage

```bash
# Fetch and categorize all failed packages (aarch64 and unsafe builder auto-skipped)
python3 ~/.qoder/skills/arch4edu-mid-fixer/scripts/fetch-status.py

# JSON output for programmatic use
python3 ~/.qoder/skills/arch4edu-mid-fixer/scripts/fetch-status.py --json

# Filter by specific category
python3 ~/.qoder/skills/arch4edu-mid-fixer/scripts/fetch-status.py --category "Failed in build()"

# Show all statuses (not just FAILED)
python3 ~/.qoder/skills/arch4edu-mid-fixer/scripts/fetch-status.py --all

# Show SCHEDULED packages (potential stuck builds)
python3 ~/.qoder/skills/arch4edu-mid-fixer/scripts/fetch-status.py --status SCHEDULED

# Show skipped packages (aarch64 and unsafe builder)
python3 ~/.qoder/skills/arch4edu-mid-fixer/scripts/fetch-status.py --show-skipped

# Show priority ranking by downstream blocker count
python3 ~/.qoder/skills/arch4edu-mid-fixer/scripts/fetch-status.py --priority
```

## Status Data Source

All status data comes from:

```
https://api.arch4edu.org/status/builds.json
```

This JSON endpoint returns the full build status for all packages in the arch4edu repository, including:
- `key` — package path (e.g. `x86_64/r/r-rlang`)
- `status` — build status (PUBLISHED, FAILED, SCHEDULED, BUILDING, etc.)
- `detail` — failure detail message (for FAILED packages)
- `updated` — last update timestamp

## Priority

Packages are prioritized by a two-tier system:

### Tier 1: Architecture Priority

1. **`any/` packages first** — Architecture-independent packages are always fixed before `x86_64/` packages. They build faster, are shared across architectures, and unblock more downstream builds.
2. **`x86_64/` packages second** — Architecture-specific packages are fixed after all `any/` failures are resolved.

### Tier 2: Failure Category Priority (within same architecture)

Within the same architecture, failures are prioritized by category:

1. **Failed in package()** — Highest priority. The build succeeded but packaging failed. Usually a simple fix (missing file, wrong path, missing depends).
2. **Failed in build()** — Medium priority. Build failures that may need PKGBUILD patches or additional makedepends.
3. **Build failed.** (generic) — No specific category in `detail`, only "Build failed." message. Requires log investigation (`gh run view <id> --log | grep -i error`) to determine root cause. Treat as build() priority after investigation.
4. **Other failures** (sources, prepare) — Lowest priority.

### Downstream Blocker Count

Within the same tier, packages are further ranked by downstream blocker count — how many STALE packages are `Waiting for dependency: <key>`. More blockers = higher priority. Fixing one high-blocker package can unblock dozens of downstream builds.

Each package in the output is annotated with `[N blocked]` when it blocks N other packages. The `--priority` flag shows a dedicated ranking view.

## Failure Categories

The following categories are identified from the `detail` field of FAILED packages:

| Category | Pattern in detail | Notes |
|----------|-------------------|-------|
| Missing dependencies | `Missing dependencies:` | Extract dep names after colon |
| Failed in check() | `Failed in check()` | Test failures |
| Failed in gpg() | `Failed in gpg()` | GPG signature issues |
| Failed in sources() (R CRAN) | `Failed in sources()` | Only for R CRAN packages (path contains `/r/`) |
| Failed in checksums() | `Failed in checksums()` | Checksum mismatches |
| Failed in build() | `Failed in build()` | Build failures, may contain missing R deps |
| Failed in prepare() | `Failed in prepare()` | Prepare phase failures |
| Failed in package() | `Failed in package()` | Packaging phase failures |
| Other | (none of above) | Unclassified failures |

## Fix Workflow

When fixing a failed package, follow these steps in order:

### Step 1: Clone from AUR

```bash
mkdir -p ~/aur && cd ~/aur
git clone https://aur.archlinux.org/<pkgname>.git
```

If the directory already exists, `git pull` to update.

### Step 2: Reproduce with smart-build

```bash
cd ~/aur/<pkgname>/
SMART_BUILD_NOCHECK=1 ~/.qoder/skills/smart-build/scripts/smart-x86_64-build
```

- Check `build-v*.log` for the failure. Set up `build-monitor -w "<window-name>"` immediately after launch.
- **Version mismatch**: If the build fails at sources() due to a 404 (upstream version updated), manually update `_cranver`/`pkgver` and `sha256sums` in the PKGBUILD first. Check the current source URL with `curl -sI <url>` and get the new checksum with `curl -sL <url> | sha256sum`.
- Confirm the failure matches the `detail` from builds.json before proceeding.

### Step 3: Fix PKGBUILD and verify

Edit the PKGBUILD in `~/aur/<pkgname>/` to fix the root cause. Common fixes:

- **Typos in variable names**: e.g. `${scrdir}` → `${srcdir}`
- **Missing patches**: add `sed`, `patch`, or other fixes
- **Build script errors**: adjust configure flags, add missing deps, etc.

Rebuild after each change:

```bash
SMART_BUILD_NOCHECK=1 ~/.qoder/skills/smart-build/scripts/smart-x86_64-build
```

Repeat until `grep -q '==> Running checkpkg' build-v*.log` returns success.

### Step 4: Write fix to cactus.yaml

Translate the PKGBUILD change into a `pre_build` command in the repo's `cactus.yaml`. The fix runs after `aur-pre-build` (which fetches the AUR sources) and before the build.

```yaml
pre_build: |
  aur-pre-build
  replace -u '1.2-1' '1.2-2'       # version update (if needed)
  sed -i 's/scrdir/srcdir/g' PKGBUILD  # the actual fix
```

**cactus.yaml fix constraints (LLM review will reject violations):**

1. **No new files** — Do not add extra files (e.g. patch copies) to the repo package directory. All fixes must be done inline via `sed`.
2. **AUR deps go in cactus.yaml `depends`/`makedepends` fields** — These fields control AUR build dependency injection in the chroot. Do not sed PKGBUILD for deps.
3. **Official deps use `add` command** — When PKGBUILD is missing an official Arch dependency, inject it in pre_build with `add makedepends <pkg>` or `add depends <pkg>`. See `skill cactus-yaml-manual`.
4. **Keep pre_build minimal** — Only do the necessary source patches.

Common `pre_build` fix patterns:

| PKGBUILD change | pre_build command |
|-----------------|-------------------|
| Fix typo/word in PKGBUILD | `sed -i 's/old/new/g' PKGBUILD` |
| Replace a line | `sed -i '/pattern/c\replacement' PKGBUILD` |
| Add a line after pattern | `sed -i '/pattern/a\new line' PKGBUILD` |
| Delete lines from a file | `sed -i '6,7d' fix-tests.patch` |
| Fix patch file for new version | `sed -i 's/old_pattern/new_pattern/' patch-file` |
| Version update | `replace -u 'old-ver' 'new-ver'` |
| Add missing AUR dependency | Add to cactus.yaml `depends` list (NOT sed on PKGBUILD) |
| Add missing official makedepend | `add makedepends <pkg>` (e.g. `add makedepends python-setuptools`) |
| Add missing official depend | `add depends <pkg>` (e.g. `add depends wxwidgets-gtk3`) |

**Important**: Use plain `replace` (not `replace -u`) for non-version substitutions like hash fixes.

**cactus.yaml format reference**: When the fix pattern is unclear, consult `skill cactus-yaml-manual` for full field descriptions and decision rules.

### Step 5: Simulate pre_build and verify

After writing the fix to cactus.yaml, simulate the pre_build locally to verify the sed commands work correctly before committing.

```bash
cd ~/aur/<pkgname>/

# 1. Reset to AUR original state (replaces aur-pre-build)
git checkout -- PKGBUILD
# Also reset other files if pre_build modifies them:
# git checkout -- fix-tests.patch

# 2. Run pre_build commands (skip aur-pre-build, skip replace -u if source is already updated)
# Execute each sed/patch command from cactus.yaml pre_build manually:
sed -i '...' PKGBUILD

# 3. Verify the fix was applied correctly
grep -n '<expected-change>' PKGBUILD

# 4. Build to confirm
SMART_BUILD_NOCHECK=1 ~/.qoder/skills/smart-build/scripts/smart-x86_64-build
```

If the build fails, fix the sed commands in cactus.yaml and repeat this step.

### Step 6: Commit and push

```bash
cd ~/cactus_bot/repo
OPENCLAW_AGENT_NAME=cactus git pull --rebase
OPENCLAW_AGENT_NAME=cactus git add <path>/cactus.yaml
OPENCLAW_AGENT_NAME=cactus git commit -m "fix(<pkgname>): <short description>"
OPENCLAW_AGENT_NAME=cactus git push    # timeout 600000ms — triggers LLM review + Feishu approval
```

- The push triggers automated code review and Feishu approval (usually 30-60s).
- If push is rejected (remote has new commits), `pull --rebase` and retry.
- Always set Bash timeout to `600000` for `git push` — the review pipeline is slow.

### Step 7: Trigger rebuild

```bash
python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <full-path>
```

Example: `python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py x86_64/r/r-uuid`

Monitor with: `gh run view <run-id> --repo arch4edu/cactus`

## Related Skills

- **aur-cli** — Query AUR package metadata, dependencies, maintainer info.
- **trigger-rebuild** — Re-trigger package builds after fixes.
- **smart-add-package** — Add new packages with automatic dependency resolution.
- **smart-build** — Build packages with real-time monitoring.
- **arch4edu-junior-fixer** — Handles simpler, deterministic fix categories.
- **cactus-yaml-manual** — cactus.yaml format reference and decision rules for dependency mechanisms.
