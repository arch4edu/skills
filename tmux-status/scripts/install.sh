#!/bin/bash
# Universal installer for tmux-status hooks
# Supports: Qoder CLI, Claude Code, Codex CLI
set -e

SCRIPTS_DIR="$HOME/.config/tmux-status"
CLEAR_SCRIPT="$SCRIPTS_DIR/tmux-window-clear.sh"
NAME_SCRIPT="$SCRIPTS_DIR/tmux-window-name.sh"

mkdir -p "$SCRIPTS_DIR"

# --- Write clear script ---
cat > "$CLEAR_SCRIPT" << 'SCRIPT'
#!/bin/bash
name="$1"
pane="$2"
if [[ "$name" == "✨"* ]]; then
    tmux rename-window -t "$pane" "${name#✨}"
elif [[ "$name" == "🔥"* ]]; then
    : # still running, keep 🔥
fi
SCRIPT
chmod +x "$CLEAR_SCRIPT"

# --- Write name script ---
cat > "$NAME_SCRIPT" << SCRIPT
#!/bin/bash
input=\$(cat)
cwd=\$(echo "\$input" | jq -r '.cwd')
base=\$(basename "\${QODER_PROJECT_DIR:-\$cwd}")
mode="\${1:-idle}"

tmux set-hook -g after-select-window \\
  "run-shell '$CLEAR_SCRIPT \"#{window_name}\" \"#{pane_id}\"'" 2>/dev/null
tmux set-hook -g after-select-pane \\
  "run-shell '$CLEAR_SCRIPT \"#{window_name}\" \"#{pane_id}\"'" 2>/dev/null

target_pane="\${TMUX_PANE}"
current=\$(tmux display-message -t "\$target_pane" -p '#{window_name}' 2>/dev/null) || exit 0

case "\$mode" in
  active) target="🔥\$base" ;;
  done)
    # Only touch window if it currently shows our own 🔥 (another pane's session may own it)
    if [[ "\$current" != "🔥\$base" ]]; then exit 0; fi
    active=\$(tmux display-message -t "\$target_pane" -p '#{window_active} #{session_active}' 2>/dev/null)
    [ "\$active" = "1 1" ] && target="\$base" || target="✨\$base"
    ;;
  *) target="\$base" ;;
esac

[ "\$current" != "\$target" ] && tmux rename-window -t "\$target_pane" "\$target"
exit 0
SCRIPT
chmod +x "$NAME_SCRIPT"

# --- Hook config snippet (identical JSON for all tools) ---
HOOKS_JSON=$(python3 - "$NAME_SCRIPT" << 'PYEOF'
import json, sys
s = sys.argv[1]
print(json.dumps({
    "UserPromptSubmit": [{"async": True, "hooks": [{"type": "command", "command": f"{s} active"}]}],
    "Stop":             [{"async": True, "hooks": [{"type": "command", "command": f"{s} done"}]}],
    "StopFailure":      [{"async": True, "hooks": [{"type": "command", "command": f"{s} done"}]}],
    "SessionStart":     [{"async": True, "hooks": [{"type": "command", "command": f"{s} idle"}]}],
    "SessionEnd":       [{"async": True, "hooks": [{"type": "command", "command": f"{s} idle"}]}],
}))
PYEOF
)

# --- Merge helper ---
merge_hooks() {
    local config_file="$1"
    local tool_name="$2"
    mkdir -p "$(dirname "$config_file")"
    python3 - "$config_file" "$HOOKS_JSON" << 'PYEOF'
import json, sys

config_file, hooks_json = sys.argv[1], sys.argv[2]
new_hooks = json.loads(hooks_json)

try:
    with open(config_file) as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {}

existing = cfg.get("hooks", {})
for event, groups in new_hooks.items():
    kept = [g for g in existing.get(event, [])
            if not any("tmux-window-name.sh" in h.get("command", "") for h in g.get("hooks", []))]
    kept.extend(groups)
    existing[event] = kept

cfg["hooks"] = existing
with open(config_file, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF
    echo "  $tool_name: $config_file"
}

echo "Installing tmux-status hooks..."

# Qoder CLI
if [ -d "$HOME/.qoder" ] || command -v qodercli &>/dev/null; then
    merge_hooks "$HOME/.qoder/settings.json" "Qoder CLI"
fi

# Claude Code
if [ -d "$HOME/.claude" ] || command -v claude &>/dev/null; then
    merge_hooks "$HOME/.claude/settings.json" "Claude Code"
fi

# Codex CLI
if [ -d "$HOME/.codex" ] || command -v codex &>/dev/null; then
    merge_hooks "$HOME/.codex/hooks.json" "Codex CLI"
fi

echo "Done. Restart your AI CLI session(s) to activate."
