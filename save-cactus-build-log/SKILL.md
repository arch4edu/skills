---
name: save-cactus-build-log
description: Save clean build logs from arch4edu/cactus GitHub Actions workflow runs to /tmp/<run-id>.log. By default filters to the Build step only, stripping timestamps, ANSI codes, and GitHub Actions boilerplate. Use whenever you need to inspect or debug a cactus builder workflow run.
---

# Save Cactus Build Log

## Overview

Saves build logs from arch4edu/cactus GitHub Actions workflow runs to `/tmp/<run-id>.log`. By default, filters the log to show only the **Build step** output, with timestamps, ANSI color codes, and GitHub Actions boilerplate removed.

The full workflow log typically has ~1500 lines but the Build step is only ~40-100 lines. This skill saves just the relevant build output.

**Script location**: `~/.qoder/skills/save-cactus-build-log/save-log`

## Usage

```bash
# Save clean build log (default: build step only)
~/.qoder/skills/save-cactus-build-log/save-log <run-id>

# Full workflow log (no filtering)
~/.qoder/skills/save-cactus-build-log/save-log <run-id> -f

# Raw output (keep timestamps and ANSI codes)
~/.qoder/skills/save-cactus-build-log/save-log <run-id> -r

# Specify a different repository
~/.qoder/skills/save-cactus-build-log/save-log <run-id> -R owner/repo

# Custom output directory
~/.qoder/skills/save-cactus-build-log/save-log <run-id> -o ~/logs
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `-R <owner/repo>` | Repository to query | `arch4edu/cactus` |
| `-o <dir>` | Output directory | `/tmp` |
| `-f` | Full log (no build-step filtering) | off |
| `-r` | Raw output (keep timestamps and ANSI) | off |
| `-h` | Show help | — |

## Output

- File saved to `<output-dir>/<run-id>.log`
- Stdout prints the file path, line count, and filter ratio on success
- Stderr prints error details on failure (partial output still saved if available)

## Log Format

The `gh run view --log` output uses tab-separated fields:

```
<job-name>\t<step-name>\t<timestamp><message>
```

The Build step is identified by step names starting with `Build ` (e.g., `Build aarch64/teamviewer`).

## Examples

```bash
# Save clean build log
save-log 27096257642
# => Build log saved to: /tmp/27096257642.log (10 lines, filtered from 1451)

# Full log with cleaning
save-log 27096257642 -f
# => Log saved to: /tmp/27096257642.log (1451 lines)

# Save log from a different repo
save-log 1234567890 -R arch4edu/packages

# After saving, search for errors
grep -i "error" /tmp/27096257642.log
```

## When to Use

- Debugging a failed cactus package build
- Checking build output for a specific package
- Saving clean logs for error analysis
- Archiving logs before they expire (GitHub retains logs for a limited time)

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`)
- Read access to the target repository
