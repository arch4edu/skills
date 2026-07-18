---
name: tmux-status
description: Install hooks that sync tmux window name with cwd and agent activity across Qoder CLI, Claude Code, and Codex CLI. Shows 🔥 while working, ✨ when done but unseen, clears on window focus. Use when the user wants tmux window status indicators for any AI coding CLI.
---

# tmux-status

Universal tmux window status for AI coding CLIs.

## Behavior

| Event | Window name |
|-------|-------------|
| User submits prompt | `🔥basename(cwd)` |
| Agent finishes, window visible | `basename(cwd)` |
| Agent finishes, window not visible | `✨basename(cwd)` |
| Window gains focus | `basename(cwd)` (✨ cleared) |
| Session ends | `basename(cwd)` |

## Supported tools

| Tool | Config written |
|------|---------------|
| Qoder CLI | `~/.qoder/settings.json` |
| Claude Code | `~/.claude/settings.json` |
| Codex CLI | `~/.codex/hooks.json` |

All three use the same hook JSON format (`UserPromptSubmit` / `Stop` / `SessionEnd`).

## Install

```bash
bash ~/.qoder/skills/tmux-status/scripts/install.sh
```

Idempotent. Requires `jq`, `python3`, `tmux`. Restart CLI sessions to activate.

## Uninstall

Remove `tmux-window-name.sh` entries from each tool's config, delete `~/.config/tmux-status/`, and:

```bash
tmux set-hook -gu after-select-window
```
