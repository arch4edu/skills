---
name: cactus-yaml-manual
description: arch4edu cactus.yaml format reference. Use when fixing packages and the correct cactus.yaml pattern is unclear.
---

# cactus.yaml Manual

cactus.yaml is the per-package configuration file in the arch4edu repository (`~/cactus_bot/repo/<arch>/<pkg>/cactus.yaml`). It controls how packages are built, including dependency resolution, build options, and pre/post processing.

## Fields Reference

### `nvchecker` (required)

Controls version update checking. Usually sourced from AUR:

```yaml
nvchecker:
  - source: aur
    aur:
  - alias: python    # add for python packages
```

### `depends`

**AUR runtime dependencies only.** Each entry is a repo-relative path to another package in arch4edu.

```yaml
depends:
  - any/python-xarray-einstats
  - x86_64/libccd
```

- Used when a dependency is NOT in the official Arch repos (extra/community) and must come from arch4edu.
- Do NOT list official Arch packages here (e.g., `python-numpy`, `python-setuptools`).
- Do NOT modify PKGBUILD `depends` via sed in pre_build for these - cactus.yaml `depends` already handles injection.

### `makedepends`

**AUR build-time dependencies only.** Same path format as `depends`.

```yaml
makedepends:
  - any/pypy3-build
  - any/pypy3-installer
```

- Used when a build dependency is NOT in official Arch repos and must come from arch4edu.
- Do NOT list official Arch packages here.

### `add depends` / `add makedepends` / `add checkdepends` (in pre_build)

**Official (extra/) dependencies missing from PKGBUILD.** Use the `add` command inside `pre_build`:

```yaml
pre_build: |
  aur-pre-build
  add makedepends python-setuptools
  add depends wxwidgets-gtk3
  add checkdepends flake8
```

- `add makedepends <pkg>`: injects an official package into PKGBUILD's makedepends at build time.
- `add depends <pkg>`: injects into PKGBUILD's depends.
- `add checkdepends <pkg>`: injects into PKGBUILD's checkdepends.
- Accepts multiple packages: `add makedepends python-build python-installer python-wheel`.
- **When to use**: The PKGBUILD is missing an official Arch dependency (e.g., `python-setuptools` for `setuptools.build_meta` backend). The upstream AUR PKGBUILD has a bug - it forgot to list an official dependency.

### `build_prefix`

Build environment prefix. Standard values:

| Value | Use case |
|---|---|
| `extra-x86_64` | Most x86_64 and `any` packages (default) |
| `extra-aarch64` | aarch64 packages |
| `multilib-x86_64` | x86_64 packages with 32-bit dependencies |

### `makepkg_args`

Extra arguments passed to `makepkg`:

| Value | Effect |
|---|---|
| `--nocheck` | Skip `check()` function (disable tests) |
| `--skippgpcheck` | Skip PGP signature verification |
| `-A` | Ignore architecture restrictions (for aarch64 cross-builds) |

### `pre_build`

Shell script executed before the build. Common commands:

| Command | Purpose |
|---|---|
| `aur-pre-build` | Standard AUR setup (must be first) |
| `add makedepends <pkg>` | Add missing official build dependency |
| `add depends <pkg>` | Add missing official runtime dependency |
| `replace -u 'old' 'new'` | Version update in PKGBUILD |
| `sed -i 's/.../.../'` | Inline source patches |
| `sed -i '6,7d' file.patch` | Repair patch files for new version |

**Important**: `pre_build: aur-pre-build` (single-line) when no fixes are needed. Use multi-line `|` syntax when fixes are needed.

### `post_build`

Shell script after build. Usually `aur-post-build`.

### `group`

Runner group for CI builds:

| Value | Use case |
|---|---|
| `GitHubActions` | Default for most packages |
| `x86_64` | Complex packages needing more resources |
| `aarch64` | aarch64 packages |

## Builder Helper Commands

These commands are available on the builder's `$PATH` during `pre_build` and `post_build` execution. They operate on the current directory (the unpacked PKGBUILD working dir).

### `add`

Appends a package to a PKGBUILD array variable (depends, makedepends, checkdepends, etc.).

```
add <array_name> <pkg1> [pkg2] [pkg3] ...
```

- Writes `<array_name>+("<pkg1>" "<pkg2>" ...)` to the end of PKGBUILD, which `makepkg` interprets as appending to that array.
- **Primary use case**: injecting official Arch dependencies that the AUR PKGBUILD forgot to list.
- Accepts multiple packages in one call.

```bash
# Single package
add makedepends python-setuptools

# Multiple packages
add makedepends python-build python-installer python-wheel

# Runtime dependency
add depends wxwidgets-gtk3

# Test dependency
add checkdepends flake8
```

### `replace`

Performs a single string replacement in PKGBUILD (first occurrence only).

```
replace [-u] [-c] <old_string> <new_string>
```

| Flag | Effect |
|---|---|
| `-u` / `--update` | After replacement, run `updpkgsums` to recalculate source checksums |
| `-c` / `--check` | Exit with code 1 if `old_string` is not found (useful for detecting unexpected PKGBUILD changes) |

**Important**: Without `-u`, `replace` does NOT update checksums. Use `-u` for version updates where the source URL changes. Use plain `replace` (no `-u`) for non-version substitutions like hash fixes or string patches.

```bash
# Version update (updates checksums automatically)
replace -u '2.1.0' '2.2.0'

# Non-version string replacement (no checksum update)
replace 'old-sha256-hash' 'new-sha256-hash'

# Check that a string exists before replacing
replace -c 'deprecated_flag' 'new_flag'
```

### `aur-pre-build`

Standard AUR source fetcher. Almost always the first command in `pre_build`:

1. Runs `git-rm-all` (cleans the working directory).
2. Runs `download-aur-snapshot` (downloads and extracts the AUR package tarball).
3. Removes `.gitignore`.
4. Records the file list in `.cactus_filelist`.

The optional argument overrides the AUR package name (defaults to the directory name).

```yaml
pre_build: |
  aur-pre-build
  # ... fixes ...
```

### `aur-post-build`

Standard post-build processing. Almost always the value of `post_build`.

```yaml
post_build: aur-post-build
```

### `recv-gpg-keys`

Imports all GPG keys listed in PKGBUILD's `validpgpkeys` array. Use when the build fails at the `gpg()` step.

```yaml
pre_build: |
  aur-pre-build
  recv-gpg-keys
```

### `auto-bump-pkgrel`

Automatically bumps `pkgrel` in PKGBUILD if the new version is not greater than the old version (version downgrade protection). Takes `old_version` and `new_version` as arguments.

```bash
auto-bump-pkgrel "1.2-1" "1.2-1"   # bumps pkgrel to 2
```

### `read-version`

Reads the current `epoch:pkgver-pkgrel` from PKGBUILD using `makepkg --printsrcinfo`. Returns the full version string.

```bash
read-version   # outputs e.g. "2.1.0-3"
```

### `set-swap`

Configures swap space on the builder. Takes a size argument (e.g., `4G`). Used when builds require more memory than available RAM.

```yaml
pre_build: |
  aur-pre-build
  set-swap 4G
```

### `download-aur-snapshot`

Downloads and extracts an AUR package snapshot tarball. Retries up to 5 times. Called by `aur-pre-build`; rarely used directly.

```bash
download-aur-snapshot python-numpy   # downloads python-numpy from AUR
```

## Decision Rules

### Which dependency mechanism to use?

```
Is the missing dependency an official Arch package (in extra/community)?
  YES -> use `add makedepends <pkg>` or `add depends <pkg>` in pre_build
  NO  -> is it available in arch4edu repo?
    YES -> add to cactus.yaml `depends` or `makedepends` field (repo path)
    NO  -> the dependency itself needs to be added to arch4edu first
```

### When PKGBUILD has a build error:

1. **Missing official dependency** (e.g., `setuptools.build_meta`, `cmake` too old):
   - Use `add makedepends <pkg>` in pre_build
   - Example: `add makedepends python-setuptools`

2. **Source code needs patching** (e.g., typos, API changes):
   - Use `sed -i` in pre_build for inline patches
   - Example: `sed -i 's/scrdir/srcdir/g' PKGBUILD`

3. **Version mismatch** (AUR PKGBUILD outdated):
   - Use `replace -u 'old_ver' 'new_ver'` in pre_build

4. **Tests failing** (non-critical):
   - Add `makepkg_args: --nocheck` to cactus.yaml

5. **CMake policy warning** (cmake 4.x):
   - Use sed to add `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` to cmake flags

## Template Symlinks

When a package needs no extra cactus.yaml configuration, its `cactus.yaml` is a symlink to a template (e.g., `../../template/x86_64-simple.yaml`).

**Warning**: Before editing a symlinked cactus.yaml, delete the symlink and create an independent file. Editing a symlink modifies the template, affecting all packages that use it.

## Examples

### Python package missing setuptools in makedepends

```yaml
nvchecker:
  - source: aur
    aur:
  - alias: python
depends:
  - any/python-xarray-einstats
build_prefix: extra-x86_64
pre_build: |
  aur-pre-build
  add makedepends python-setuptools
post_build: aur-post-build
```

### Package needing source patch + extra dependency

```yaml
nvchecker:
  - source: aur
    aur:
build_prefix: extra-x86_64
pre_build: |
  aur-pre-build
  sed -i 's/scrdir/srcdir/g' PKGBUILD
  add makedepends cmake
post_build: aur-post-build
```

### Package with version update + patch repair

```yaml
nvchecker:
  - source: aur
    aur:
build_prefix: extra-x86_64
pre_build: |
  aur-pre-build
  replace -u '3.6.4' '3.6.5'
  sed -i '6,7d' fix-tests.patch
post_build: aur-post-build
```

### Package with AUR dependencies

```yaml
nvchecker:
  - source: aur
    aur:
depends:
  - any/pypy3-mpmath
makedepends:
  - any/pypy3-build
  - any/pypy3-installer
  - any/pypy3-setuptools
build_prefix: extra-x86_64
pre_build: aur-pre-build
post_build: aur-post-build
```
