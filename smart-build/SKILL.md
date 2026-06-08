---
name: smart-build
description: >-
  Build arch4edu packages using smart-x86_64-build with tmux integration and monitoring support.
  Use when the user asks to build a package, start a build, monitor a build, or check build status.
  Covers launch, build monitoring, and completion detection.
---

# Smart Build

## Overview

Build arch4edu packages via `smart-x86_64-build` - a wrapper that analyzes
AUR dependencies, selects the right build tool (extra-x86_64-build or arch4edu-x86_64-build),
launches the build in a tmux `build` session window, and logs output to auto-incremented `build-vN.log` files.

## Key Tools

| Tool | Location | Purpose |
|------|----------|---------|
| smart-x86_64-build | `scripts/smart-x86_64-build` | Build launcher with tmux integration |
| show-aur-dependency | `scripts/show-aur-dependency` | Analyze AUR dependency availability |
| smart-build-monitor.sh | `scripts/smart-build-monitor.sh` | Periodic status polling |
| arch4edu-x86_64-build | `/usr/bin/arch4edu-x86_64-build` (system) | Chroot-based arch4edu builder |

## Workflow

### 1. Launch

```bash
cd ~/aur/<package>/
smart-x86_64-build
```

**Allowed directories**: `~/aur`

The script runs in foreground, launches the build in a tmux `build` session window, then returns immediately. No need to run in background - read the foreground output for window name, log path, and monitoring hint.

The script:
- Analyzes dependencies via `show-aur-dependency`
- Selects build tool based on AUR dep availability in arch4edu
- Backs up PKGBUILD -> `PKGBUILD.bakN`
- Launches build in tmux window (auto-closes on finish)
- Tee to `build-vN.log` (auto-incremented)
- **SMART_BUILD_NOCHECK=1** to skip check phase

### 2. Monitor (during build)

**Preferred**: Use available system monitoring tools (e.g. tmux window monitoring, event notifications) to watch the build window. Build completion is notified to the session automatically.

**Fallback**: If no monitoring tool is available, poll every ~5 minutes:

```bash
bash smart-build-monitor.sh <log-file>
```

Output (strict markdown table - report verbatim to user):

| Time | Progress | CPU | Memory | ZRAM | Battery |
|------|----------|-----|--------|------|---------|
| 14:32 | ==> Starting build()... | 85.2% | 6.2/15.5G | 2.1G/4.0G | 72% discharging |

- **Time**: HH:MM (24h)
- **Progress**: last line of log, max 60 chars
- **CPU**: usage percentage (100 - idle)
- **Memory**: used/total in GiB
- **ZRAM**: compressed/data
- **Battery**: percentage + state; N/A if unavailable

After each invocation, **read the log file to summarize current build progress**, then replace the `(see log)` placeholder with the summary and **report the completed table to the user**.

Use `sleep 300` between polls. Bash timeout: 600000ms (10 min).
Never let sleep approach the timeout limit.

**Find latest log**: `ls -lt build-v*.log | head -1`

### 3. Detect Completion

**Success**: Log contains `==> Running checkpkg`
```bash
grep -q '==> Running checkpkg' <log-file> && echo "SUCCESS"
```

**Failure**: Log contains `==> ERROR: A failure occurred`
```bash
grep -n '==> ERROR\|CMake Error\|Failed' <log-file>
```

**Process check**:
```bash
ps aux | grep arch4edu-x86_64-build | grep -v grep
```

### 4. Diagnose Failures

```bash
# Find error lines with context
grep -n '==> ERROR\|CMake Error\|Failed' <log-file>

# Last 50 lines for context
tail -50 <log-file>

# Check if process is still running
ps aux | grep arch4edu-x86_64-build | grep -v grep
```

Common failures -> use `arch4edu-junior-fixer` skill for auto-fix.

### 5. Post-Build

- Built packages: `*.pkg.tar.zst` in current directory
- checkpkg compares against arch4edu repo (new packages show "target not found" - expected)
- Only `cactus.yaml` should be committed to arch4edu repo, NOT PKGBUILD changes
- PKGBUILD changes go in `cactus.yaml` pre_build scripts

## Key Constraints

- Only ONE build at a time (chroot limitation)
- smart-x86_64-build runs in foreground, build executes in tmux build session
- No env vars needed for smart-x86_64-build (unlike some other builders)
