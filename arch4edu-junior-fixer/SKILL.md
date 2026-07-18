---
name: arch4edu-junior-fixer
description: Auto-fix common arch4edu build failures: Missing dependencies, Failed in check(), Failed in gpg(), Failed in sources() (R CRAN 404), Failed in checksums, R package missing deps from Failed in build() logs. Fetches builds.json, categorizes failures, and applies fixes. Use when user asks to fix failed builds, auto-fix, junior fix, or batch fix packages.
---

# Arch4edu Junior Fixer

## Overview

Automated fix for common, low-risk arch4edu build failures. Handles 6 fixable categories with deterministic rules. Skips anything requiring version constraints or complex debugging.

## Usage

```bash
# Per-category analysis scripts (all support --json for JSON output)
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-missing-dependency.py
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-r-dependency.py
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-check.py
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-gpg.py
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-r-sources.py
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-checksums.py
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-stuck.py
```

### Script Summary

| Script | Category | Purpose |
|--------|----------|---------|
| `_common.py` | (shared) | Shared utilities: fetch_builds, check_dep_in_repo, fetch_build_log_deps |
| `fix-missing-dependency.py` | Missing dependencies | Checks deps for version constraints, repo presence, PUBLISHED status. R packages with deps not in repo → smart-add-package. Non-R x86_64 with leaf AUR deps → manual add |
| `fix-r-dependency.py` | R dependency issues | R Failed in build() missing deps. Deps not in repo → smart-add-package |
| `fix-check.py` | Failed in check() | Lists all fixable packages (add --nocheck) |
| `fix-gpg.py` | Failed in gpg() | Lists all fixable packages (add --skippgpcheck) |
| `fix-r-sources.py` | Failed in sources() | R CRAN packages only, skips non-R |
| `fix-checksums.py` | Failed in checksums() | Auto-checks maintainer via aur-cli, skips arch4edu members |
| `fix-stuck.py` | Stuck SCHEDULED/BUILDING | Detects SCHEDULED >1h and BUILDING >6h, lists packages needing trigger-rebuild |

## Fixable Categories — Detailed Instructions

### 1. Missing dependencies

**Step 1:** Extract missing dependency names from the `detail` field.
Example: `Missing dependencies: python-ibm-quantum-schemas, python-pybase64` → extract `python-ibm-quantum-schemas`, `python-pybase64`

**Step 2:** Check if each dependency exists in the repo and is PUBLISHED.

- **All deps PUBLISHED in repo (any package type):** Direct add — go to Step 3.
- **R package with deps NOT in repo:** Use `smart-add-package` (Step 2a) — it resolves from AUR.
- **Non-R x86_64 package with leaf AUR deps NOT in repo:** Manual add (Step 2b).
- **Non-R package with deps NOT in repo (non-leaf AUR):** Skip — too complex, needs manual analysis.

**Skip if:**
- Dependency status is not PUBLISHED (for direct-add path)
- Requires version constraint (e.g. `dart<3.12.0`)

**Step 2a — R package missing dependencies (deps not in repo, use smart-add-package):**

For R packages where one or more dependencies are NOT yet in the arch4edu repo but exist in AUR, run `smart-add-package` on the **existing failing package** (not the missing dep). The script will resolve the full dependency tree from AUR and add any missing packages automatically.

```bash
cd ~/cactus_bot/repo
python3 smart-add-package.py -t template/x86_64-nocheck.yaml x86_64/r/<failing-package>
```

After running, check the target package diff — only depends/makedepends/checkdepends changes are expected. Revert any other changes.

If a missing dependency is not in AUR, the script will error out. That package needs manual handling.

**Step 2b — Non-R x86_64 packages with leaf AUR deps (deps not in repo):**

For non-R x86_64 packages where missing dependencies exist in AUR and those dependencies do NOT depend on other AUR packages (leaf AUR), manually add the deps:

1. Create new package directories with symlink to the appropriate template:
```bash
cd ~/cactus_bot/repo
mkdir -p x86_64/<dep-name>
# Choose template based on package type:
#   Default:       x86_64-simple.yaml
#   R packages:    x86_64-nocheck.yaml
#   Python packages: x86_64-python.yaml
ln -s ../../template/x86_64-simple.yaml x86_64/<dep-name>/cactus.yaml
```

2. Add dep reference to failing package's cactus.yaml:
```yaml
depends:
  - x86_64/<existing-dep>
  - x86_64/<new-leaf-aur-dep>  # new
```

**Note:** If the failing package's cactus.yaml is a symlink to a template, delete the symlink and create an independent cactus.yaml first.

**Skip** non-R packages with deps not in repo AND deps are not leaf AUR — too complex, needs manual analysis.

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

- **All deps PUBLISHED in repo:** Direct add (Step 3).
- **Deps NOT in repo:** Use `smart-add-package` on the failing package — it resolves from AUR.
  ```bash
  cd ~/cactus_bot/repo
  python3 smart-add-package.py -t template/<arch>-nocheck.yaml <pkg_key>
  ```
  After running, check diff — only depends/makedepends/checkdepends changes are expected. Revert any other changes.

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

**Step 4 — Archived packages (no new version):**

When a CRAN package returns 404 and is NOT in the current `PACKAGES` list but IS available in the CRAN Archive directory (`https://cran.r-project.org/src/contrib/Archive/<pkgname>/`), the package has been archived without a newer version.

**Verification steps:**
```bash
# Check if package is 404 on main CRAN
curl -sI "https://cran.r-project.org/src/contrib/<pkgname>_<version>.tar.gz" | head -3

# Check if it's in the Archive
curl -sI "https://cran.r-project.org/src/contrib/Archive/<pkgname>/<pkgname>_<version>.tar.gz" | head -3

# Confirm it's not in current PACKAGES list
curl -s "https://cran.r-project.org/src/contrib/PACKAGES" | grep -A2 "^Package: <pkgname>$"
```

**Fix:** Add a `replace` directive in pre_build to redirect the source URL from `contrib/` to `Archive/<pkgname>/`:

```yaml
pre_build: |
  aur-pre-build
  replace 'https://cran.r-project.org/src/contrib/' 'https://cran.r-project.org/src/contrib/Archive/<pkgname>/'
```

Use plain `replace` (not `replace -u`) since the version hasn't changed — only the URL path changes.

**Note:** If the package's cactus.yaml is a symlink to a template, delete the symlink and create an independent cactus.yaml file (same rules as other categories).

**Skip if:** Not an R CRAN package, or package is archived on CRAN AND not available in the Archive directory.

### 6. Failed in checksums()

**Step 1:** Use aur-cli to check if the package is maintained by arch4edu members (petronny, carlosal1015, AutoUpdateBot).
```bash
aur-cli get-info --package <pkgname> --json
```

**Skip if:** Maintained by arch4edu members — they self-fix.

**Step 1b:** Check AUR comments — if someone has already reported the checksum issue and it's been less than 2 weeks, skip (wait for maintainer to respond).

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

### 7. Stuck SCHEDULED/BUILDING

When a package has been stuck in SCHEDULED (>1 hour) or BUILDING (>6 hours), it likely needs a rebuild trigger.

**Step 1:** Run the detection script:
```bash
python3 ~/.qoder/skills/arch4edu-junior-fixer/scripts/fix-stuck.py
```

**Step 2:** For each stuck package, use trigger-rebuild to re-trigger:
```bash
python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <full-path>
```

**Note:** BUILDING packages with age < 6h may still be compiling normally (e.g. openfoam, large C++ projects). Use judgement before triggering.

### 8. ABI incompatibility (lazy loading failed)

When R packages fail with `lazy loading failed` due to ABI incompatibility (e.g. after R or r-rlang upgrade):

**Step 1:** Identify the root package that needs rebuilding (e.g. `r-rlang`, `r-cpp11`).

**Step 2:** Trigger rebuild for the root package first:
```bash
python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py x86_64/r/r-rlang
```

**Step 3:** After the root package succeeds, re-trigger the dependent packages.

## Skip Rules

- Packages requiring version constraints (e.g. `=v2506`) — cactus.yaml doesn't support them
- Non-R package dependencies not in repo — too complex, needs manual analysis. Exception: x86_64 leaf AUR deps (deps in AUR with no AUR sub-dependencies) can be manually added. R packages with deps not in repo use smart-add-package (resolves from AUR)
- Failed in build() / prepare() / package() — too complex, needs manual analysis (except R package missing deps pattern)
- "Failed to download dependencies" — transient, rerun may work
- Maintained by arch4edu members (petronny, carlosal1015, AutoUpdateBot) — skip, they self-fix
- R CRAN packages archived on CRAN AND not available in the Archive directory — skip

## Workflow

**Principle: process one category at a time. Commit, push, then move to the next.** Do not mix fixes from different categories in the same commit.

1. Pick one category by priority, run the analysis script, confirm the fixable list
2. Apply fixes for that category (edit cactus.yaml)
3. Commit all changes for that category in a single commit
4. Push (pull --rebase first; remote limits one commit per push, squash if needed)
5. Wait for push to succeed, then move to the next category
6. Trigger rebuild for fixed packages:
   - **Existing packages** (already in builds.json): use `trigger-rebuild` skill:
     ```bash
     python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <pkgbase>
     ```
   - **Newly added packages**: no trigger needed — committing cactus.yaml to the repo is sufficient, the build system will pick them up automatically.

**Recommended category order:**
1. Failed in check() — simplest, just add --nocheck
2. Failed in gpg() — simple, just add --skippgpcheck
3. Missing dependencies — requires verifying dep status
4. R package missing deps (Failed in build()) — requires log inspection
5. Failed in sources() — requires aur-cli version check
6. Failed in checksums() — requires maintainer verification and hash calculation

## Related Skills

- **aur-cli** — Used for querying AUR package metadata, dependencies, maintainer info, and version numbers.
  - `aur-cli get-info --package <pkgname> --json` — Get full package info
  - `aur-cli search --package <pkgname>` — Search for package existence
  - Use aur-cli instead of web scraping AUR

- **trigger-rebuild** — Used to re-trigger package builds after fixes are applied.
  - `python3 ~/.qoder/skills/trigger-rebuild/scripts/trigger-rebuild.py <pkgbase>` — Rebuild a package
  - First tries `gh run rerun` (90-day retention), falls back to `trigger_js.yml` workflow dispatch
  - **Limitation:** Only works for packages already in builds.json. Newly added packages don't need any trigger — committing cactus.yaml to the repo is sufficient.

## Template Selection

When creating new packages (symlinks) or using `smart-add-package`, choose the template based on package type:

| Package Type | Template | Example |
|-------------|----------|---------|
| Default (non-R, non-Python) | `x86_64-simple.yaml` | `x86_64/qt5-charts/cactus.yaml` → `../../template/x86_64-simple.yaml` |
| R packages (`/r/` path) | `x86_64-nocheck.yaml` | `x86_64/r/r-foo/cactus.yaml` → `../../template/x86_64-nocheck.yaml` |
| Python packages (`python-*`) | `x86_64-python.yaml` | `x86_64/python-foo/cactus.yaml` → `../../template/x86_64-python.yaml` |

**smart-add-package usage:**
```bash
# R package
python3 smart-add-package.py -t template/x86_64-nocheck.yaml x86_64/r/<pkg>
# Python package
python3 smart-add-package.py -t template/x86_64-python.yaml x86_64/python-<pkg>
# Default
python3 smart-add-package.py -t template/x86_64-simple.yaml x86_64/<pkg>
```

**Symlink creation:**
```bash
# R package
ln -s ../../template/x86_64-nocheck.yaml x86_64/r/<pkg>/cactus.yaml
# Python package
ln -s ../../template/x86_64-python.yaml x86_64/python-<pkg>/cactus.yaml
# Default
ln -s ../../template/x86_64-simple.yaml x86_64/<pkg>/cactus.yaml
```

## Key Files

- `cactus.yaml` — per-package config, edit directly for existing files
- Symbolic links to templates — delete link, create independent cactus.yaml
- Never edit template files (affects all packages using that template)

## Architecture Isolation

- aarch64 packages cannot reference x86_64 dependencies
- x86_64 packages cannot reference aarch64 dependencies
- `any` category packages can be referenced by any architecture
