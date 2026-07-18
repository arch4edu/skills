# AGENTS.md

This file provides guidance to the AI agent when working with code in this repository.

## What This Repo Is

A collection of Qoder CLI skills for managing arch4edu (Arch Linux education repo). Each skill is a directory containing a `SKILL.md` and optional `scripts/` folder.

## Skill Structure

- `SKILL.md` must have YAML frontmatter with `name` and `description` fields
- Scripts go in `<skill-name>/scripts/`
- Python scripts use `python3`, support `--json` flag for machine-readable output
- Shared utilities live in `scripts/_common.py` within the skill that owns them

## Commit Style

Conventional commits with skill name as scope:

```
feat(<skill-name>): <description>
fix(<skill-name>): <description>
chore: <description>
```

## Key External Paths (referenced by skills, not in this repo)

- `~/bin/aur-cli` - AUR query tool (always use this, never AUR RPC directly)
- `~/aur/<pkg>/` - cloned AUR package working directories
- `~/.qoder/skills/` - this repo's install location

## Code Style Rules

- No Chinese in SKILL.md, scripts, or commit messages -- English only
- No absolute paths in code -- use `~/` or relative paths
- Plain ASCII only (no em dashes, smart quotes, etc.)

## Gotchas

- `config.py` is gitignored (contains secrets) - never commit it
