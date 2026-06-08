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

1. Run the script to add the package
2. Review the generated cactus.yaml
3. **Check target package diff**: run `git diff <target-path>/cactus.yaml` - only depends/makedepends/checkdepends changes are expected. Revert any other changes (e.g., nvchecker, build_prefix, makepkg_args, pre_build, post_build) with `git checkout -- <target-path>/cactus.yaml` and manually re-apply only the dep changes
4. Commit the new package directory
5. Push to trigger build

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
