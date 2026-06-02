#!/usr/bin/env python3
"""
Git helper functions — platform-agnostic.
Used by all notification backends (feishu, telegram, etc.).
"""

import os
import subprocess


def get_git_diff(max_bytes=30000):
    """Get diff of the last commit, truncated to max_bytes."""
    try:
        commit_hash = subprocess.run(
            ['git', 'log', '-1', '--format=%H'],
            capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()

        stat = subprocess.run(
            ['git', 'show', '--stat', '--format=%h   %s%n%an <%ae>', commit_hash],
            capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()

        diff = subprocess.run(
            ['git', 'show', '--pretty=', '-p', commit_hash],
            capture_output=True, text=True, check=True, timeout=30
        ).stdout.strip()

        combined = f"{stat}\n\n---\n\n{diff}"

        if len(combined.encode('utf-8')) > max_bytes:
            diff_bytes = diff.encode('utf-8')
            stat_bytes = stat.encode('utf-8')
            prefix_bytes = "\n\n---\n\n".encode('utf-8')
            max_diff = max_bytes - len(stat_bytes) - len(prefix_bytes)
            if max_diff > 100:
                diff = diff_bytes[:max_diff].decode('utf-8', errors='replace') + '\n... (truncated)'
            combined = f"{stat}\n\n---\n\n{diff}"

        return commit_hash, combined
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff: {e}")
        return None, None


def get_push_details():
    """Get remote URL, repo name, and default branch."""
    try:
        remote_url = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        repo_name = remote_url.split('/')[-1].replace('.git', '')
        try:
            default_branch = subprocess.run(
                ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                capture_output=True, text=True
            ).stdout.strip().replace('refs/remotes/origin/', '')
        except:
            default_branch = 'master'
        return remote_url, repo_name, default_branch
    except subprocess.CalledProcessError:
        return 'unknown', 'unknown', 'master'


def get_commit_author_name():
    """Get the author name of the last commit."""
    try:
        return subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%an'],
            capture_output=True, text=True, check=True, timeout=10
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return "bot"


def get_commit_author_email():
    """Get the author email of the last commit."""
    try:
        return subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%ae'],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except:
        return ""


def get_repo_info():
    """Get repo folder name, current branch and remote."""
    try:
        remote_name = 'origin'
        try:
            upstream = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', '@{upstream}'],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            if '/' in upstream:
                remote_name = upstream.split('/')[0]
        except:
            pass

        try:
            current_branch = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
        except:
            current_branch = 'unknown'

        return os.getcwd().split('/')[-1], current_branch, remote_name
    except:
        return "unknown", "unknown", "origin"


def check_remote_ahead(default_branch='master'):
    """Check if local is ahead of remote. Returns (ok, message).

    ok=True: safe to push
    ok=False: blocked (behind or diverged)
    """
    try:
        subprocess.run(['git', 'fetch', 'origin'], capture_output=True, timeout=30)

        # If default_branch is empty, try to find it
        if not default_branch:
            result = subprocess.run(
                ['git', 'remote', 'show', 'origin'],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.split('\n'):
                if 'HEAD branch:' in line:
                    default_branch = line.split(':', 1)[1].strip()
                    break

        # Still empty? Remote might be empty (first push) — allow
        if not default_branch:
            return True, ""

        remote_head = subprocess.run(
            ['git', 'rev-parse', f'origin/{default_branch}'],
            capture_output=True, text=True
        ).stdout.strip()
        local_head = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True
        ).stdout.strip()

        # Remote branch doesn't exist yet (first push to empty repo) — allow
        if not remote_head or remote_head == local_head:
            return True, ""

        merge_base = subprocess.run(
            ['git', 'merge-base', 'HEAD', f'origin/{default_branch}'],
            capture_output=True, text=True
        ).stdout.strip()

        if merge_base == local_head == remote_head:
            return True, ""
        elif merge_base == local_head and merge_base != remote_head:
            return False, (
                f"Local branch is behind remote.\n"
                f"   Local:  {local_head[:8]}\n"
                f"   Remote: {remote_head[:8]}\n"
                f"   Please pull first: git pull --rebase origin {default_branch}"
            )
        elif merge_base != local_head and merge_base != remote_head:
            return False, (
                f"Branches have diverged (non-fast-forward).\n"
                f"   Local:  {local_head[:8]}\n"
                f"   Remote: {remote_head[:8]}\n"
                f"   Please rebase or merge remote changes first."
            )

        return True, ""
    except Exception as e:
        return True, f"Warning: Failed to check remote: {e}"


def count_commits_ahead(default_branch='master'):
    """Count commits ahead of remote. Returns list of commit lines."""
    try:
        commits = subprocess.run(
            ['git', 'log', f'origin/{default_branch}..HEAD', '--oneline'],
            capture_output=True, text=True
        ).stdout.strip().split('\n')
        return [c for c in commits if c]
    except:
        return []


def check_pkgbuild_in_repo():
    """When folder is named 'repo', block PKGBUILD additions or modifications."""
    repo_name = os.path.basename(os.getcwd())
    if repo_name != 'repo':
        return True, ""

    try:
        diff = subprocess.run(
            ['git', 'diff', '--cached', '--name-status'],
            capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:
        return True, ""

    if not diff:
        return True, ""

    for line in diff.split('\n'):
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        status = parts[0].upper()
        filepath = parts[1]
        basename = os.path.basename(filepath)

        if basename == 'PKGBUILD' and status in ('A', 'M'):
            return False, f"PKGBUILD cannot be {'added' if status == 'A' else 'modified'} in 'repo' folder"

    return True, ""
