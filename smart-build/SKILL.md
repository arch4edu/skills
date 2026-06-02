---
name: smart-build
description: >-
  Build arch4edu packages using smart-x86_64-build in foreground with real-time monitoring.
  Use when the user asks to build a package, start a build, monitor a build, or check build status.
  Covers launch, periodic progress polling, resource tracking, and completion detection.
---

# Smart Build

## Overview

Build arch4edu packages via `smart-x86_64-build` — a foreground wrapper that analyzes
AUR dependencies, selects the right build tool (extra-x86_64-build or arch4edu-x86_64-build),
and logs output to auto-incremented `build-vN.log` files.

## Key Tools

| Tool | Location | Purpose |
|------|----------|---------|
| smart-x86_64-build | `~/.qoder/skills/smart-build/scripts/smart-x86_64-build` | Foreground build with dependency analysis |
| show-aur-dependency | `~/.qoder/skills/smart-build/scripts/show-aur-dependency` | Analyze AUR dependency availability |
| smart-build-monitor.sh | `~/.qoder/skills/smart-build/scripts/smart-build-monitor.sh` | Periodic status polling |
| arch4edu-x86_64-build | `/usr/bin/arch4edu-x86_64-build` (system) | Chroot-based arch4edu builder |

## Workflow

### 1. Launch

```bash
cd ~/aur/<package>/
~/.qoder/skills/smart-build/scripts/smart-x86_64-build
```

**Allowed directories**: `~/aur`

The script:
- Analyzes dependencies via `show-aur-dependency`
- Selects build tool based on AUR dep availability in arch4edu
- Backs up PKGBUILD → `PKGBUILD.bakN`
- Runs in foreground, tee to `build-vN.log` (auto-incremented)
- **SMART_BUILD_NOCHECK=1** to skip check phase

### 2. Monitor (during build)

Every ~5 minutes, run:

```bash
bash ~/.qoder/skills/smart-build/scripts/smart-build-monitor.sh <log-file>
```

Output format:

| 时间 | 构建进度 | CPU | 内存 | ZRAM | 电量 |
|------|----------|-----|------|------|------|

- **Build progress**: `tail -3 <latest-log>`
- **CPU**: `top -bn1 | grep Cpu`
- **Memory**: `free -h`
- **ZRAM**: `zramctl`
- **Battery**: `upower -i /org/freedesktop/UPower/devices/battery_BAT0 | grep -E 'state|percentage|time to'`

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

Common failures → use `arch4edu-junior-fixer` skill for auto-fix.

### 5. Post-Build

- Built packages: `*.pkg.tar.zst` in current directory
- checkpkg compares against arch4edu repo (new packages show "target not found" — expected)
- Only `cactus.yaml` should be committed to arch4edu repo, NOT PKGBUILD changes
- PKGBUILD changes go in `cactus.yaml` pre_build scripts

## Key Constraints

- Only ONE build at a time (chroot limitation)
- smart-x86_64-build runs in foreground — do NOT use submit-x86_64-build (background tmux)
- Monitoring interval: 300s, Bash timeout: 600000ms
- No env vars needed for smart-x86_64-build (unlike some other builders)
