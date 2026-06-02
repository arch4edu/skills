---
name: trigger-rebuild
description: Trigger a rebuild for a package in arch4edu/cactus. First tries gh run rerun (within 90-day retention). Falls back to trigger_js.yml workflow dispatch. Use when user asks to rebuild, re-run, retry, re-trigger, or restart a package build. Requires full package path (e.g. x86_64/r/r-rlang, aarch64/flutter).
---

# Trigger Rebuild

## Overview

Re-trigger package builds in arch4edu/cactus with automatic fallback.

## Usage

Run the helper script:

```bash
python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <full-path>
```

Requires full path:
- `x86_64/r/r-rlang`
- `aarch64/flutter`
- `any/python-tokenizers`

Short names (e.g. `r-rlang`) are NOT accepted.

## Flow

1. **Lookup** — Query `api.arch4edu.org/status/builds.json` for package info
2. **Rerun** — Try `gh run rerun <workflow_id>` (works within 90-day GitHub retention)
3. **Fallback** — If rerun fails/expired, `gh workflow run trigger_js.yml --field pkgbase=<path>` marks package STALE → build system auto-schedules new build

## Verify

```bash
# Find a FAILED package first
curl -s https://api.arch4edu.org/status/builds.json | python3 -c "
import json,sys
d=json.load(sys.stdin)
for e in d['packages']:
  if e['status']=='FAILED': print(f\"{e['key']}: {e['status']}\"); break
"

# Test with that FAILED package (replace with actual key from above)
python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py x86_64/<failed-pkg>

# Check workflow run
gh run view <run_id> --repo arch4edu/cactus
```

## Key Facts

- `trigger_js.yml` calls `arch4edu/cactus/actions/update-status-js@main` to set status=STALE
- Detector/Scheduler detect STALE and queue a new build
- No version bump needed — trigger_js works even if AUR version unchanged (e.g. ABI rebuild after R upgrade)
- Build time: typically 2-5 minutes for R packages
