---
name: arch4edu-junior-fixer
description: Auto-fix common arch4edu build failures: Missing dependencies, Failed in check(), Failed in gpg(), Failed in sources() (R CRAN 404), Failed in checksums, R package missing deps from Failed in build() logs. Fetches builds.json, categorizes failures, and applies fixes. Use when user asks to fix failed builds, auto-fix, junior fix, or batch fix packages.
---

# Arch4edu Junior Fixer

## Overview

Automated fix for common, low-risk arch4edu build failures. Handles 6 fixable categories with deterministic rules. Skips anything requiring version constraints or complex debugging.

## Usage

```bash
# 1. Quick overview: categorize all FAILED packages (sources() only shows R CRAN)
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fetch-failed.py

# 2. Full analysis: which packages are actually fixable and why others are skipped
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/analyze-fixes.py

# 3. Check specific package dependencies
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/check-deps.py x86_64/r/r-vcdextra

# 4. Check ALL Missing dependencies packages
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/check-deps.py --all

# JSON output (for all scripts that support it)
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/analyze-fixes.py --json
```

### Script Summary

| Script | Purpose |
|--------|---------|
| `fetch-failed.py` | Quick categorization of FAILED packages from builds.json. Filters sources() to R CRAN only. Detects R package missing deps from build() detail. |
| `analyze-fixes.py` | Full analysis: checks deps availability, version constraints, maintainer status. Shows fixable vs skipped. |
| `check-deps.py` | Deep-dive into specific Missing dependencies packages. Shows each dep's repo status. |

## Fixable Categories — Detailed Instructions

### 1. Missing dependencies

**Step 1:** Extract missing dependency names from the `detail` field.
Example: `Missing dependencies: python-ibm-quantum-schemas, python-pybase64` → extract `python-ibm-quantum-schemas`, `python-pybase64`

**Step 2:** Check if each dependency exists in the repo and is PUBLISHED.

**Skip if:**
- Dependency not in repo
- Dependency status is not PUBLISHED
- Requires version constraint (e.g. `dart<3.12.0`)

**Step 3:** Query AUR to confirm if it's a runtime dependency (depends) or build-time dependency (makedepends).
```bash
aur-cli get-info --package <dep-name> --json
```

**Step 4:** Edit the package's `cactus.yaml`:
```yaml
depends:
  - x86_64/python-qiskit
  - x86_64/python-ibm-quantum-schemas  # new
makedepends:
  - x86_64/python-pybase64  # new
```

**Architecture rule:** aarch64 packages reference `aarch64/<category>/<dep>`, x86_64 packages reference `x86_64/<category>/<dep>`.

### 2. R package missing deps (Failed in build())

When an R package fails in build(), the build log may contain errors like:
```
ERROR: dependency 'X' is not available for package 'Y'
```

**Step 1:** Check builds.json detail field for `dependency 'X' is not available` pattern. If not present in detail, fetch the build log from the workflow URL and extract missing deps.

**Step 2:** Check if each missing dep is in repo and PUBLISHED.

**Step 3:** Add to cactus.yaml depends:
```yaml
depends:
  - x86_64/r/r-rcpp
  - x86_64/r/r-generics  # new
```

**Note:** The dependency name in the error is the R package name (e.g. `generics`, `RcppParallel`), convert to lowercase with `r-` prefix for the repo path (e.g. `x86_64/r/r-generics`).

### 3. Failed in check()

**Direct fix:** Add `makepkg_args: --nocheck` to cactus.yaml.

```yaml
build_prefix: extra-x86_64
makepkg_args: --nocheck
pre_build: aur-pre-build
```

If `makepkg_args` already exists, append `--nocheck` to the existing value.

### 4. Failed in gpg()

**Direct fix:** Add `makepkg_args: --skippgpcheck` to cactus.yaml.

```yaml
build_prefix: extra-x86_64
makepkg_args: --skippgpcheck
pre_build: aur-pre-build
```

If `makepkg_args` already exists (e.g. `--nocheck`), combine: `makepkg_args: --nocheck --skippgpcheck`.

### 5. Failed in sources() — R CRAN packages (404)

**Step 1:** Confirm it's an R CRAN package (path contains `/r/`).

**Step 2:** Use aur-cli to find the new version.
```bash
aur-cli get-info --package r-<pkgname> --json
```

**Step 3:** Add version update to pre_build in cactus.yaml.
```yaml
pre_build: |
  aur-pre-build
  replace -u '0.9.0' '0.10.0'
```

The `replace -u` command updates the version string and automatically recalculates checksums via `updpkgsums`.

**Skip if:** Not an R CRAN package, or package is archived on CRAN with no new version.

### 6. Failed in checksums()

**Step 1:** Use aur-cli to check if the package is maintained by arch4edu members (petronny, carlosal1015, AutoUpdateBot).
```bash
aur-cli get-info --package <pkgname> --json
```

**Skip if:** Maintained by arch4edu members — they self-fix.

**Step 2:** Download the source and calculate the correct checksum.
```bash
curl -L <source-url> -o source.tar.gz
sha256sum source.tar.gz
```

**Step 3:** Add checksum fix to pre_build in cactus.yaml.
```yaml
pre_build: |
  aur-pre-build
  replace 'old_wrong_hash' 'new_correct_hash'
```

**Note:** Use plain `replace` (not `replace -u`) since we know the correct hash.

## Skip Rules

- Packages requiring version constraints (e.g. `=v2506`) — cactus.yaml doesn't support them
- Dependencies not in repo — skip, can't fix
- Failed in build() / prepare() / package() — too complex, needs manual analysis (except R package missing deps pattern)
- "Failed to download dependencies" — transient, rerun may work
- Maintained by arch4edu members (petronny, carlosal1015, AutoUpdateBot) — skip, they self-fix
- R CRAN packages archived on CRAN with no new version — skip

## Workflow

1. Run `fetch-failed.py` or `analyze-fixes.py` to get candidate list
2. For each fixable category, apply the corresponding fix to cactus.yaml
3. Commit all changes in a single commit
4. Push (pull --rebase first, remote allows one commit at a time, squash if needed)
5. Trigger rebuild for fixed packages using the `trigger-rebuild` skill:
   ```bash
   python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <pkgbase>
   ```

## Related Skills

- **aur-cli** — Used for querying AUR package metadata, dependencies, maintainer info, and version numbers.
  - `aur-cli get-info --package <pkgname> --json` — Get full package info
  - `aur-cli search --package <pkgname>` — Search for package existence
  - Use aur-cli instead of web scraping AUR

- **trigger-rebuild** — Used to re-trigger package builds after fixes are applied.
  - `python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <pkgbase>` — Rebuild a package
  - First tries `gh run rerun` (90-day retention), falls back to `trigger_js.yml` workflow dispatch

## Key Files

- `cactus.yaml` — per-package config, edit directly for existing files
- Symbolic links to templates — delete link, create independent cactus.yaml
- Never edit template files (affects all packages using that template)

## Architecture Isolation

- aarch64 packages cannot reference x86_64 dependencies
- x86_64 packages cannot reference aarch64 dependencies
- `any` category packages can be referenced by any architecture
