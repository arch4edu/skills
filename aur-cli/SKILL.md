---
name: aur-cli
description: Read-only AUR package querying. get-info for metadata/dependencies, get-source for PKGBUILD/.SRCINFO, get-flag-comment for OOD flags, search-by-co-maintainer for maintainer packages. Use whenever you need AUR package information — never use web scraping or AUR RPC API directly.
---

# AUR CLI

## Overview

Read-only tool to query AUR package information. Located at `~/bin/aur-cli`.

**MANDATORY: Always use `~/bin/aur-cli` for AUR queries. Never use web scraping, AUR RPC API directly, or other methods.**

## Commands

### get-info

Get package metadata, dependencies, and sources.

```bash
# Human-readable
~/bin/aur-cli get-info --package <pkgname>

# JSON output (for parsing)
~/bin/aur-cli get-info --package <pkgname> --json
```

Returns: metadata (version, maintainer, URL, etc.), dependencies (depends/makedepends/checkdepends), optional dependencies, required_by count, sources.

### get-source

Get raw file content from AUR git repo (PKGBUILD, .SRCINFO, etc.).

```bash
# Get PKGBUILD (default)
~/bin/aur-cli get-source --package <pkgname>

# Get .SRCINFO
~/bin/aur-cli get-source --package <pkgname> --file .SRCINFO

# Get any file in the repo
~/bin/aur-cli get-source --package <pkgname> --file <filepath>

# JSON output
~/bin/aur-cli get-source --package <pkgname> --file .SRCINFO --json
```

### get-flag-comment

Check if package is flagged out-of-date and get the reason.

```bash
~/bin/aur-cli get-flag-comment --package <pkgname>
```

Returns: "Package X is not flagged." or flag date, author, and reason.

### search-by-co-maintainer

Find all packages co-maintained by a specific user.

```bash
~/bin/aur-cli search-by-co-maintainer --maintainer <name>
```

## Common Use Cases in arch4edu Workflow

1. **Check depends vs makedepends**: Use `get-source --file .SRCINFO` to see standardized dependency types
2. **Get checksums**: Use `get-source` to get PKGBUILD, then read sha256sums
3. **Check if package is outdated**: Use `get-flag-comment`
4. **Get package version**: Use `get-source --file .SRCINFO` and read pkgver
5. **Check dependencies**: Use `get-info --json` for structured dependency data

## Notes

- Automatically handles Anubis (Arch Linux anti-bot) challenges
- Saves cookies to `~/.config/aurcli/cookies.json` after solving challenges
- All operations are read-only — no login or write capabilities
- Dependencies from `.SRCINFO` distinguish: `depends` (runtime), `makedepends` (build-time), `checkdepends` (test-time), `optdepends` (optional)
