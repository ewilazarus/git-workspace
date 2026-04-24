#!/bin/bash

# Runs when a workspace is being removed.
#
# This hook is intended for final cleanup that should only happen when the
# worktree is about to be deleted. It runs after `on_detach`, so any
# interactive or runtime state should already be shut down.
#
# Keep this focused on removal-specific tasks. For general shutdown (services,
# tmux, etc.), prefer `on_detach`.
#
# Common use cases:
# - Clean up external resources tied to this workspace
# - Log or notify that the workspace is being deleted
#
# Example:
# rm -rf .cache/dev || true

echo "Running teardown ..."
