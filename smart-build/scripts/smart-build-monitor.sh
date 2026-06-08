#!/usr/bin/env bash
# smart-build-monitor.sh - Monitor a running smart-x86_64-build process
#
# Usage: smart-build-monitor.sh <log-file>
#
# Strict output format - 3 parts:
#
# 1. Log excerpt (last 20 lines):
#   === Log (last 20 lines) ===
#   ...build output...
#   ===========================
#
# 2. Markdown table:
#   | Time  | Progress                | CPU    | Memory     | ZRAM       | Battery           |
#   |-------|-------------------------|--------|------------|------------|-------------------|
#   | 14:32 | (please summarize ...)  | 85.2%  | 6.2/15.5G  | 2.1G/4.0G  | 72% discharging   |
#
# 3. Action instruction:
#   ACTION: Summarize the build progress from the log in a few words,
#   replace the placeholder above, and report the completed table exactly to the user.
#
# Field rules:
#   Time         - HH:MM (24h)
#   Progress     - placeholder; agent MUST read the log and summarize build progress
#   CPU          - usage percentage (100 - idle), e.g. "85.2%"
#   Memory       - used/total in GiB, e.g. "6.2/15.5G"
#   ZRAM         - compressed/data, e.g. "2.1G/4.0G"
#   Battery      - percentage + state, e.g. "72% discharging"; "N/A" if unavailable
#
# The agent MUST report this table verbatim to the user after each invocation.

set -uo pipefail

LOG_FILE="${1:?Usage: $0 <log-file>}"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "ERROR: Log file not found: $LOG_FILE"
    exit 1
fi

# Progress: placeholder - agent should read the log and summarize
progress="(please summarize from the log in a few words)"

# CPU: usage percentage (100 - idle)
# Force English locale so top always shows "id" (not locale-specific labels)
cpu=$(LANG=C top -bn1 2>/dev/null | awk '/^%?Cpu/ {gsub(/,/,"",$0); for(i=1;i<=NF;i++) if($i ~ /^id$/) {printf "%.1f%%", 100-$(i-1); exit}}')
[[ -z "$cpu" ]] && cpu="N/A"

# Memory: used/total in GiB
mem=$(LANG=C free -g 2>/dev/null | awk '/^Mem:/ {printf "%.1f/%.1fG", $3, $2}')
[[ -z "$mem" ]] && mem="N/A"

# ZRAM: compressed/data
zram=$(zramctl --noheadings 2>/dev/null | awk '{printf "%s/%s", $5, $4}' | tr '\n' ' ' | sed 's/[[:space:]]*$//')
[[ -z "$zram" ]] && zram="N/A"

# Battery: percentage (rounded to int) + state
battery=$(upower -i /org/freedesktop/UPower/devices/battery_BAT0 2>/dev/null | awk '
    /percentage/ {gsub(/%/,"",$2); pct=int($2+0.5); print pct; exit}
')
bat_state=$(upower -i /org/freedesktop/UPower/devices/battery_BAT0 2>/dev/null | awk '/state:/ {print $2; exit}')
if [[ -n "$battery" && -n "$bat_state" ]]; then
    battery="${battery}% ${bat_state}"
else
    battery="N/A"
fi

now=$(date '+%H:%M')

# Log excerpt for agent to summarize
echo "=== Log (last 20 lines) ==="
tail -20 "$LOG_FILE"
echo "==========================="
echo ""

# Markdown table output - single row
echo "| Time | Progress | CPU | Memory | ZRAM | Battery |"
echo "|------|----------|-----|--------|------|---------|"
printf "| %s | %s | %s | %s | %s | %s |\n" "$now" "$progress" "$cpu" "$mem" "$zram" "$battery"
echo ""
echo "ACTION: Summarize the build progress from the log in a few words, replace the placeholder above, and report the completed table exactly to the user."
