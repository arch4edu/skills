---
name: arch4edu-storage
description: Upload source tarballs to arch4edu/storage GitHub Releases for packages whose upstream sources are inaccessible to the arch4edu/cactus build system. Use when a PKGBUILD source URL is dead, geo-blocked, or requires authentication, and the tarball needs to be mirrored to a stable URL.
---

# arch4edu-storage

Mirror inaccessible source tarballs to GitHub Releases.

## Storage location

- Repo: `arch4edu/storage`
- Local clone: `~/git/storage`
- Download URL: `https://github.com/arch4edu/storage/releases/download/<tag>/<filename>`

## Upload workflow

```bash
# tag convention: <pkgname>
gh release create <pkgname> /path/to/source.tar.gz \
  --repo arch4edu/storage \
  --notes "<pkgname> <pkgver> upstream mirror"
```

## Update PKGBUILD source

Replace the dead URL with the release download URL:

```bash
source=("https://github.com/arch4edu/storage/releases/download/<pkgname>/<filename>")
```

## Download during build

The `builder/bin/arch4edu-storage` command automatically downloads mirrored sources. It parses the source URL from `.SRCINFO` or `PKGBUILD`, resolves `$pkgver`/`$pkgname` variables, handles `filename::url` syntax, and downloads the matching asset from `arch4edu/storage`.

```bash
# Usage: arch4edu-storage <pkgname> [index]
#   index: 1-based source number (default: 1)
arch4edu-storage openfst
arch4edu-storage some-pkg 2   # download 2nd source
```

In `cactus.yaml`:

```yaml
pre_build: arch4edu-storage openfst
```

If the asset is not found in storage, the command exits silently (no error).

## Notes

- Max 2GB per file
- Releases are permanent while the repo exists
- Use descriptive tag names to avoid collisions (include pkgname)
