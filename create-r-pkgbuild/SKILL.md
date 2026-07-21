---
name: create-r-pkgbuild
description: Generate a PKGBUILD for an R CRAN package. Scrapes CRAN metadata (version, description, license, dependencies) and outputs a ready-to-use PKGBUILD. Use when the user asks to create, generate, or scaffold a PKGBUILD for an R package from CRAN.
---

# Create R PKGBUILD

## Overview

Generates a PKGBUILD for an R package by scraping its CRAN page, then builds and verifies it. Handles recursive dependency creation for r- packages not yet on AUR. Located at `~/.qoder/skills/create-r-pkgbuild/create-r-pkgbuild.py`.

## Usage

```bash
python3 ~/.qoder/skills/create-r-pkgbuild/create-r-pkgbuild.py <cran_package_name>
```

The argument is the CRAN package name (case-sensitive as listed on CRAN), e.g. `audio`, `beepr`, `mirt`.

Output is a complete PKGBUILD printed to stdout. Redirect to a file:

```bash
python3 ~/.qoder/skills/create-r-pkgbuild/create-r-pkgbuild.py mirt > PKGBUILD
```

## What it does

1. Fetches `https://cran.r-project.org/package=<name>`
2. Parses version, description, license, Imports, and Suggests
3. Maps R license strings to Arch license identifiers
4. Converts dependencies to `r-<name>` format (lowercased)
5. Outputs a PKGBUILD with `build()` and `package()` functions

## Workflow

### 1. Clone package directory

```bash
cd ~/aur
git clone ssh://aur@aur.archlinux.org/r-<pkgname>.git
```

### 2. Install git hooks

Run the `install-git-hooks` skill in the package directory to set up push approval and commit notification hooks before any work begins.

### 3. Generate PKGBUILD

Run the script to produce the initial PKGBUILD:

```bash
python3 ~/.qoder/skills/create-r-pkgbuild/create-r-pkgbuild.py <CranName> > PKGBUILD
```

### 4. Resolve dependencies recursively

Check all `depends` and `optdepends` entries (r- packages) against AUR using the AUR RPC batch query:

```bash
curl -s "https://aur.archlinux.org/rpc/v5/info?arg[]=r-foo&arg[]=r-bar" | python3 -c "..."
```

For any r- dependency NOT on AUR, recursively create it first (depth-first, leaf nodes first). Only proceed to build the parent after all leaf dependencies are committed and available in the arch4edu repo.

### 5. Build and verify with smart-build

Use the `smart-build` skill to build the package. If the build fails, fix the PKGBUILD iteratively (adjust deps, remove unneeded makedepends, fix license, etc.) and rebuild until it passes.

If a dependency has been built locally but is not yet in the arch4edu repo, bypass smart-build's dep check and use the build tool directly with `-I` to install the local package:

```bash
arch4edu-x86_64-build -- -I ~/aur/r-<dep>/r-<dep>-<ver>-<arch>.pkg.tar.zst
```

### 6. Commit strategy: leaf-first

- Only commit a package after its build verification passes.
- Commit leaf nodes (packages with no unresolved r- deps) first.
- After a leaf node commit succeeds, you can build the parent immediately using `-I` with the local .pkg.tar.zst (no need to wait for arch4edu propagation).
- If a parent cannot be completed for other reasons, record it as a TODO and inform the user.

### 7. Track pending work

Maintain a TODO list of packages that are blocked waiting for leaf nodes to appear in arch4edu. When the user reports that a leaf is available, resume building the blocked parent.

## Notes

- Requires Python packages: `requests`, `beautifulsoup4`
- License mapping covers common GPL variants; unknown licenses are passed through as-is
- `makedepends` defaults to `(gcc-fortran)`; adjust manually if not needed
- The generated PKGBUILD uses `_cranname` and `_pkgver` variables for easy updates
- A single invocation may not complete the full tree if leaf propagation takes time; this is expected
