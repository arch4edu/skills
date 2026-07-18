---
name: arch4edu-llm-review
description: >-
  Review arch4edu/AUR code changes using a dedicated subagent. Spawns an independent
  agent to review git diffs for correctness, minimal changes, and commit message quality.
  Use when user asks to review changes, check a diff, or before pushing arch4edu packages.
---

# Arch4edu LLM Review

## Overview

Spawn a dedicated subagent (via the Agent tool) to independently review staged or
committed git diffs. The agent runs in isolation with fresh context, ensuring an
unbiased review unaffected by the current session's reasoning.

## When to Use

- Before pushing arch4edu/AUR package changes
- When user asks to "review", "check my diff", or "audit changes"
- As a manual alternative to the pre-push hook's built-in LLM review

## Critical Rule

**The review MUST run in a separate Agent with its own independent context.**
Never review in the current session. The reviewing agent must not share context,
reasoning, or bias from the session that produced the changes. This is the entire
point of the skill -- an independent second pair of eyes.

## Workflow

### Step 1: Get the diff and compute hash

The hash MUST match the pre-push hook's algorithm exactly. The hook combines
`git show --stat` output with the raw diff, separated by `\n\n---\n\n`:

```bash
# Compute the hash (same algorithm as pre-push hook)
COMMIT=$(git log -1 --format=%H)
STAT=$(git show --stat --format="%h   %s%n%an <%ae>" "$COMMIT")
DIFF=$(git show --pretty= -p "$COMMIT")
COMBINED="${STAT}

---

${DIFF}"
DIFF_HASH=$(printf '%s' "$COMBINED" | sha256sum | cut -c1-16)
```

The hash is the first 16 chars of sha256 of the combined stat+diff output.
Pass the raw diff (not the combined content) and the hash to the agent.

### Step 2: Spawn an independent review agent

Call the Agent tool with subagent_type "general-purpose". The agent starts with
zero context about why the changes were made -- it judges purely on the diff.

Do NOT:
- Review inline in the current session
- Summarize the diff before sending (send raw diff)
- Add your own justification to the prompt

The agent prompt MUST include the review rules below verbatim, followed by the raw diff.

## Review Rules

These rules MUST be included in the agent prompt exactly as written:

1. Commit message must be a single line
2. Commit message must match the actual changes
3. Changes must be correct and reasonable
4. No unnecessary or unrelated changes
5. No superfluous comment modifications
6. Changes must be minimal -- no scope creep

### Special cases (do NOT reject these)

- nvchecker `aur:` field is allowed to be empty (`aur: ` is valid)
- PKGBUILD pkgver/pkgrel bumps with corresponding checksum updates are expected
- Adding `--nocheck` or `--skippgpcheck` to fix build failures is acceptable
- cactus.yaml depends/makedepends changes that mirror PKGBUILD deps are expected
- Removing patches that are no longer needed after version bumps is correct

### Output format

The agent MUST respond in this exact format:

```
RESULT: accept | reject
REASON: <explanation when reject, brief confirmation when accept>
```

### Agent prompt structure

The agent must receive the raw diff AND the diff hash (precomputed by the parent
session). The agent writes to Redis itself on accept.

```
You are a strict code review expert for arch4edu/AUR packages.
You have NO context about why these changes were made. Judge solely on the diff.

Rules:
1. Commit message must be a single line
2. Commit message must match the actual changes
3. Changes must be correct and reasonable
4. No unnecessary or unrelated changes
5. No superfluous comment modifications
6. Changes must be minimal -- no scope creep

Special cases (do NOT reject):
- nvchecker "aur:" field is allowed to be empty ("aur: " is valid)
- PKGBUILD pkgver/pkgrel bumps with corresponding checksum updates are expected
- Adding --nocheck or --skippgpcheck to fix build failures is acceptable
- cactus.yaml depends/makedepends changes that mirror PKGBUILD deps are expected
- Removing patches that are no longer needed after version bumps is correct

After reviewing, if your verdict is "accept", you MUST write the review record
to Redis by running this command:

  redis-cli SETEX "llm_review:<DIFF_HASH>" 3600 '{"result": "accept", "reason": "Reviewed by arch4edu-llm-review skill"}'

Replace <DIFF_HASH> with: <the hash provided below>

If your verdict is "reject", do NOT write to Redis.

Respond in this exact format:
RESULT: accept | reject
REASON: <explanation>

Diff hash: <hash>

Diff:
<raw diff>
```

### Step 3: Report result

- If RESULT is "accept": report pass. The agent has already written to Redis.
- If RESULT is "reject": show the REASON to the user and suggest fixes.

## Notes

- The parent session precomputes the diff hash and passes it to the agent.
  The agent writes to Redis itself -- this keeps the review self-contained.
- For large diffs (>30KB), split by file and spawn one review agent per file.
  Each agent writes its own Redis record only if it accepts.
- The pre-push hook reads the Redis record written by this skill. If no record
  exists, the hook blocks the push and tells the user to run this skill first.
- If Redis is unavailable, the agent should report this in its REASON field.
