---
name: smart-add-package
description: Add new packages to arch4edu/cactus repo with automatic dependency resolution. Uses smart-add-package.py to resolve AUR dependencies, create cactus.yaml with proper depends/makedepends, and handle virtual packages via --provides. Use when user asks to add a package, import a package, or onboard a new package to the repo.
---

# smart-add-package

Add new packages to the arch4edu/cactus repo with automatic AUR dependency resolution.

## Overview

The script `smart-add-package.py` in the repo root:
1. Queries AUR for package dependency tree
2. Filters out packages already in Arch Linux official repos (pacman db)
3. Resolves virtual package provides
4. Creates cactus.yaml with correct depends/makedepends pointing to repo paths
5. Creates symlinks to templates for packages with no extra deps

## Usage

```bash
cd ~/cactus_bot/repo
python3 smart-add-package.py [options] <target>
```

**Target format**: `arch[/subdir/]package` (e.g., `x86_64/yay`, `any/python-foo`, `aarch64/devtools/ytmdesktop`)

## Options

| Flag | Description |
|------|-------------|
| `--template`, `-t` | Template path (default: `template/x86_64-simple.yaml`) |
| `--provides`, `-p` | Virtual package mapping. Repeatable. Format: `virtual:real` (e.g., `libjpeg:libjpeg-turbo`) or just `virtual` to read provides from pacman |
| `--nocheck` | Skip check() and ignore checkdepends. Must also use `-t template/x86_64-nocheck.yaml` |

## Templates

| Template | Use case |
|----------|----------|
| `template/x86_64-simple.yaml` | Default for x86_64 packages |
| `template/x86_64-nocheck.yaml` | x86_64 packages with check() disabled (use with `--nocheck`) |
| `template/x86_64-python.yaml` | Python packages (any arch) |
| `template/aarch64-simple.yaml` | aarch64 packages |

## Common Patterns

### Add a simple x86_64 package
```bash
python3 smart-add-package.py x86_64/yay
```

### Add a Python package (any arch)
```bash
python3 smart-add-package.py -t template/x86_64-python.yaml any/python-foo
```

### Add with nocheck (skip test suite)
```bash
python3 smart-add-package.py --nocheck -t template/x86_64-nocheck.yaml x86_64/some-package
```

### Add with virtual package provides
```bash
python3 smart-add-package.py -p libjpeg:libjpeg-turbo x86_64/some-package
```

### Add an R package
```bash
python3 smart-add-package.py -t template/x86_64-simple.yaml x86_64/r/r-newpackage
```

## Workflow

### Pre-add: Dependency Analysis

Before running smart-add-package, assess dependency complexity with aur-cli:

```bash
aur-cli get-info --package <pkgname> --json
```

Check the `dependencies` list for:
- How many deps are NOT in Arch official repos (`pacman -Si <dep>`)
- How many deps are NOT already in the cactus repo
- Whether deps have deep recursive chains

**Decision criteria:**
- Simple (0-2 missing deps): proceed directly
- Medium (3-5 missing deps): proceed, smart-add-package resolves recursively
- Complex (>5 missing deps or multi-level chains): warn user, get confirmation before proceeding

### Add: Run smart-add-package

1. Run the script to add the package (resolves deps recursively)
2. Review the generated cactus.yaml files

### Post-add: Architecture Verification

The script places packages under the target arch directory, but recursive deps
default to the same arch. Verify each new package's correct arch:

```bash
# Check arch= from AUR PKGBUILD for each new package
aur-cli get-source --package <pkgname> | grep "^arch="
```

**Rules:**
- `arch=(any)` or `arch=('any')` -> package belongs in `any/`
- `arch=(x86_64)` or contains x86_64/i686 -> package belongs in `x86_64/`
- Python packages with C/Cython extensions (cmake, cython, glibc deps) are usually x86_64

**If a package is in the wrong directory:**
```bash
mkdir -p <correct-arch>/<pkgname>
mv <wrong-arch>/<pkgname>/cactus.yaml <correct-arch>/<pkgname>/cactus.yaml
rmdir <wrong-arch>/<pkgname>
```

Then update all cactus.yaml references:
```bash
grep -r "<wrong-arch>/<pkgname>" --include="cactus.yaml" -l
# Fix each reference: <wrong-arch>/<pkgname> -> <correct-arch>/<pkgname>
```

### Commit and Push

1. **Check target package diff**: run `git diff <target-path>/cactus.yaml` - only depends/makedepends/checkdepends changes are expected. Revert any other changes (e.g., nvchecker, build_prefix, makepkg_args, pre_build, post_build) with `git checkout -- <target-path>/cactus.yaml` and manually re-apply only the dep changes
2. Commit the new package directories
3. Push to trigger build

## Important Notes

- The script must be run from the repo root (`~/cactus_bot/repo`)
- Requires `fakeroot` and `pacman` for database queries
- For `any` packages, queries x86_64 pacman database
- Dependencies already in Arch official repos are automatically excluded
- The script creates symlinks to templates when no extra deps are needed

## Verify

```bash
# Check the generated cactus.yaml
cat <target-path>/cactus.yaml

# Verify it's a valid symlink or file
ls -la <target-path>/cactus.yaml
```
