---
name: aur-cli
description: AUR package querying, login, adopt, and disown. get-info for metadata/dependencies, get-source for PKGBUILD/.SRCINFO, get-flag-comment for OOD flags, search-by-co-maintainer for maintainer packages, login for AUR authentication, adopt/disown for package maintenance. Use whenever you need AUR package information - never use web scraping or AUR RPC API directly.
---

# AUR CLI

## Overview

Tool to query AUR package information, manage login, and adopt/disown packages. Located at `~/bin/aur-cli`.

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

### login

Login to AUR with credentials from config.py and optionally save session cookies.

```bash
# Login using credentials from config.py, save cookies
~/bin/aur-cli login --save

# Login using CLI credentials (overrides config.py)
~/bin/aur-cli login --username <user> --password <pass> --save

# Login without saving cookies (session only)
~/bin/aur-cli login
```

Credentials are read from `config.py` in the skill directory (same directory as the `aur-cli` script):

```python
AUR_USERNAME = "your_aur_username"
AUR_PASSWORD = "your_aur_password"
```

CLI `--username`/`--password` overrides config.py values.

### adopt

Adopt an AUR package (become its maintainer). Requires a valid login session (run `login --save` first).

```bash
~/bin/aur-cli adopt --package <pkgname>

# JSON output
~/bin/aur-cli adopt --package <pkgname> --json
```

Automatically resolves pkgbase for split packages.

### disown

Disown an AUR package (give up maintainer status). Requires a valid login session (run `login --save` first).

```bash
~/bin/aur-cli disown --package <pkgname>

# JSON output
~/bin/aur-cli disown --package <pkgname> --json
```

Automatically resolves pkgbase for split packages.

## Common Use Cases in arch4edu Workflow

1. **Check depends vs makedepends**: Use `get-source --file .SRCINFO` to see standardized dependency types
2. **Get checksums**: Use `get-source` to get PKGBUILD, then read sha256sums
3. **Check if package is outdated**: Use `get-flag-comment`
4. **Get package version**: Use `get-source --file .SRCINFO` and read pkgver
5. **Check dependencies**: Use `get-info --json` for structured dependency data

## Notes

- Automatically handles Anubis (Arch Linux anti-bot) challenges
- Saves cookies to `~/.config/aurcli/cookies.json` after solving challenges
- `login --save` persists session cookies for use by other commands
- `adopt` and `disown` are write operations that require a valid session (run `login --save` first)
- Credentials are stored in `config.py` (same directory as the aur-cli script) - do NOT commit config.py with real credentials
- Dependencies from `.SRCINFO` distinguish: `depends` (runtime), `makedepends` (build-time), `checkdepends` (test-time), `optdepends` (optional)
