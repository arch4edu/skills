---
name: create-aur-package
description: Create a new AUR package from scratch. Clone the AUR repo, install git hooks, write PKGBUILD manually, build with smart-build until it passes, commit and push. Handles recursive dependency creation for missing deps. Use when the user asks to create, add, or package a new AUR package (non-R).
---

# Create AUR Package

## Overview

Workflow for creating a new AUR package from scratch. No template generation — the PKGBUILD is written manually based on upstream source.

## Workflow

### 1. Clone package directory

```bash
cd ~/aur
git clone ssh://aur@aur.archlinux.org/<pkgname>.git
```

### 2. Install git hooks

Run the `install-git-hooks` skill in the package directory before any work begins.

### 3. Write PKGBUILD

Create the PKGBUILD manually based on the upstream project. Determine:
- Source URL and version
- Dependencies (depends, makedepends, optdepends)
- License
- Build system (cmake, meson, make, cargo, etc.)

### 4. Resolve dependencies recursively

Check all dependencies against AUR. For any dependency NOT on AUR, create it first (depth-first, leaf nodes first). Only proceed to build the parent after all leaf dependencies are committed and available.

### 5. Build and verify with smart-build

Use the `smart-build` skill to build the package. If the build fails, fix the PKGBUILD iteratively and rebuild until it passes.

If a dependency has been built locally but is not yet in the arch4edu repo, bypass smart-build's dep check and use the build tool directly with `-I` to install the local package:

```bash
arch4edu-x86_64-build -- -I ~/aur/<dep>/<dep>-<ver>-<arch>.pkg.tar.zst
```

### 6. Commit strategy: leaf-first

- Only commit a package after its build verification passes.
- Commit leaf nodes (packages with no unresolved deps) first.
- After a leaf node commit succeeds, you can build the parent immediately using `-I` with the local .pkg.tar.zst (no need to wait for arch4edu propagation).
- If a parent cannot be completed for other reasons, record it as a TODO and inform the user.

### 7. Track pending work

Maintain a TODO list of packages that are blocked waiting for leaf nodes to appear in arch4edu. When the user reports that a leaf is available, resume building the blocked parent.

## Notes

- A single invocation may not complete the full tree if leaf propagation takes time; this is expected
- Always verify the upstream license matches what you put in the PKGBUILD
- Check existing AUR packages for reference PKGBUILDs of similar software
