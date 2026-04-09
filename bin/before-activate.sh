#!/bin/bash

# Runs before workspace activation.
#
# Use this hook to prepare interactive tooling that should exist
# before the workspace is "entered".
#
# Common use cases:
# - Create or ensure a tmux session exists
# - Start background services needed for development
# - Pre-warm caches or local tooling
#
# Example:
# tmux has-session -t dev 2>/dev/null || tmux new-session -d -s dev

echo "Running before activate ..."
