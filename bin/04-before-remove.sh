#!/bin/bash

# Runs before a workspace is removed.
#
# Use this hook to clean up resources tied to the workspace.
#
# Common use cases:
# - Stop containers or services
# - Kill tmux sessions
# - Remove temporary files or caches
#
# Example:
# docker compose down
# tmux kill-session -t dev 2>/dev/null || true

echo "Running before remove ..."
