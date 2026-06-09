---
name: qoderwake-monitor
description: "Build completion monitor: watch a tmux build session window and notify qoderwake session when it closes. Must be set up after every smart-build launch."
---

# QoderWake Monitor

## Overview

Watch a tmux `build` session window by name. When the window closes (build finished or failed), sends a notification to the qoderwake session. Runs in tmux `monitor` session.

Located at `build-monitor`.

## Usage

### Start

```bash
build-monitor "cactusreader-v1"
```

Session ID is read from `$QODER_SESSION_ID` automatically.

Runs in the tmux `monitor` session, window name matches the build window name.

### Stop

No explicit stop command. To stop a monitor, close its window in the monitor session (`tmux attach -t monitor`, then `Ctrl-b k`), or kill it directly.

### Options

| Argument | Description | Default |
|----------|-------------|---------|
| `<window-name>` | Build window name (required) | -- |

### Notification

When the watched window disappears:
```
[cactusreader-v1] Build window 'cactusreader-v1' has closed, please check the log
```

## smart-build Integration

After every `smart-build` skill launch, a `build-monitor` must be set up immediately to watch the corresponding tmux window. The window name format is `<package>-v<N>` (e.g., `cactusreader-v1`).

```bash
# After smart-build launches, the output shows the window name, e.g.:
# 📦 Build launched in tmux session 'build', window 'cactusreader-v1'

# Set up monitoring immediately
build-monitor "cactusreader-v1"
```

The monitor automatically notifies the session when the build window closes. No manual polling is needed.
