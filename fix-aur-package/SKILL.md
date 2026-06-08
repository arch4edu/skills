---
name: fix-aur-package
description: >-
  Fix AUR packages that fail to build. Workflow: clone AUR repo, install hooks,
  check upstream updates, build with smart-build, fix PKGBUILD iteratively until
  build passes, commit and push. Use when user asks to fix, repair, update, or
  unbreak an AUR package build. Triggers: "fix <pkg>", "repair <pkg>",
  "<pkg> build failed", "unbreak <pkg>".
argument-hint: <package-name>
---

# Fix AUR Package

## Overview

End-to-end workflow to fix a broken AUR package and push the repair.

## Workflow

### Step 1: Clone or Update AUR Repo

If directory does not exist:

```bash
mkdir -p ~/aur
git clone ssh://aur@aur.archlinux.org/<pkg>.git ~/aur/<pkg>
```

If directory already exists, sync to latest AUR version:

```bash
cd ~/aur/<pkg>
git pull --rebase origin master
```

### Step 2: Install Git Hooks

```bash
cd ~/aur/<pkg>
bash ~/.qoder/skills/install-git-hooks/install-git-hooks
```

### Step 3: Configure Git Author

```bash
cd ~/aur/<pkg>
git config user.name "AutoUpdateBot"
git config user.email "auto_update_bot@arch4edu.org"
```

### Step 4: Check Upstream for New Versions

Gather current AUR state:

```bash
~/bin/aur-cli get-info --package <pkg>
~/bin/aur-cli get-flag-comment --package <pkg>
```

Check the software's upstream for new releases:
- GitHub releases page (if hosted on GitHub)
- PyPI (for Python packages)
- Official project website / changelog
- RSS feeds or release tags

Compare upstream latest version with current `pkgver` in PKGBUILD.

**If upstream has a newer version**: Update PKGBUILD before building:
1. Update `pkgver` to the new version
2. Reset `pkgrel=1`
3. Update `source` URLs if needed (version in path, tag, etc.)
4. Run `updpkgsums` to regenerate checksums
5. Run `makepkg --printsrcinfo > .SRCINFO` to regenerate .SRCINFO
6. Check if upstream changelog mentions new/removed dependencies - update `depends`/`makedepends` accordingly

**If no new version**: Skip to Step 5.

Identify:
- Whether the package is flagged out-of-date (and why)
- Known build issues from AUR comments
- Dependency changes (new/removed deps)

### Step 5: Build and Fix Iteratively

Run the build:

```bash
cd ~/aur/<pkg>
~/.qoder/skills/smart-build/scripts/smart-x86_64-build
```

**On failure**:
1. Read the build log (`build-v*.log`) - find the root error
2. Edit PKGBUILD to fix the issue (patches, dependency changes, source URL updates, checksum refresh)
3. Regenerate checksums if sources changed: `updpkgsums`
4. Regenerate .SRCINFO: `makepkg --printsrcinfo > .SRCINFO`
5. Re-run smart-build
6. Repeat until build succeeds

**Common fixes**:
- Missing dependency -> add to `depends` or `makedepends`
- Source URL 404 -> update URL and run `updpkgsums`
- Checksum mismatch -> run `updpkgsums`
- Build script error -> add patches or adjust build() function
- Version bump needed -> update `pkgver`, `pkgrel=1`, sources, checksums

**Constraints**:
- Only one build at a time
- For long builds, monitor with `smart-build-monitor.sh`
- Set `SMART_BUILD_NOCHECK=1` to skip check() phase if tests are the only failure

### Step 6: Commit and Push

Once build succeeds:

```bash
cd ~/aur/<pkg>
git add -A
git commit -m "<concise one-line message describing the fix>"
git push origin master
```

**Push behavior**:
- The pre-push hook triggers LLM code review and sends a Feishu approval card
- Approval must be granted ([OK] reaction) before push completes
- **Set timeout to maximum** - use `timeout 600000` or equivalent to wait for approval
- Do NOT use `--no-verify` unless explicitly authorized by the user

**Commit message style**: single-line only. Examples:
- `Update to 1.2.3`
- `Fix build: add missing makedepends python-setuptools`
- `Fix source URL and update checksums`

## Post-Fix

After successful push:
1. Record what was fixed to the memory system (use `memory_add` with `scope=agent`, `target=daily` or `target=topic` with topic being the package name)
2. Unflag the package on AUR if it was flagged out-of-date and is now up to date
