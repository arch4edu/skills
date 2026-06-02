#!/usr/bin/env bash
# smart-build-monitor.sh — Monitor a running smart-x86_64-build process
#
# Usage: smart-build-monitor.sh <log-file> [interval_seconds]
#
# Outputs a status table row: time | build progress | CPU | memory | ZRAM | battery
# Call repeatedly during build. Default interval: 300s.

set -uo pipefail

LOG_FILE="${1:?Usage: $0 <log-file> [interval_seconds]}"
INTERVAL="${2:-300}"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "❌ Log file not found: $LOG_FILE"
    exit 1
fi

# Build progress: last 3 lines of log
progress=$(tail -3 "$LOG_FILE" 2>/dev/null | tr '\n' ' | ')

# CPU
cpu=$(top -bn1 | grep -i 'Cpu' | head -1 | sed 's/^[[:space:]]*//')

# Memory (handle both English and Chinese locale)
mem=$(LANG=C free -h | awk '/^Mem:/ {printf "Total:%s Used:%s Avail:%s", $2, $3, $7}')

# ZRAM
zram=$(zramctl --noheadings 2>/dev/null | awk '{printf "%s(%s)", $1, $4}' | tr '\n' ' ' | sed 's/[[:space:]]*$//')
if [[ -z "$zram" ]]; then
    zram="N/A"
fi

# Battery
battery=$(upower -i /org/freedesktop/UPower/devices/battery_BAT0 2>/dev/null | grep -E 'state|percentage|time to' | tr '\n' ' | ' | sed 's/[[:space:]]*$//')
if [[ -z "$battery" ]]; then
    battery="N/A"
fi

now=$(date '+%H:%M')
printf "| %s | %s | %s | %s | %s | %s |\n" "$now" "$progress" "$cpu" "$mem" "$zram" "$battery"
