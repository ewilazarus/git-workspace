#!/bin/bash

# Runs before a workspace is dettached.
#
# Use this hook to clean up resources tied to the session lifetime.
#
# Common use cases:
# - Stop containers or services
# - Kill tmux sessions
#
# Example:
# docker compose down
# tmux kill-session -t dev 2>/dev/null || true

echo "Running detach ..."
