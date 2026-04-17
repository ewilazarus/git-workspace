# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-04-16

### Changed
- Increased `prune` unit test coverage
- Base branch is pulled from origin (best-effort) before creating a new worktree

### Fixed
- Removed line breaks from `prune`, `reset`, `root` and `up` commands' help messages
- Exception when attempting to parse non-string variables from the manifest

## [0.2.0] - 2026-04-16

### Added
- Rich terminal UI: live-streaming hook output, progress bar for link application, styled branch/path colours
- `git workspace ls` renders a Rich table with Branch, Path, and Age columns, sorted by age then alphabetically
- `git workspace root` command — prints workspace root path and exits 0/1, intended for agent/scripting use
- `git workspace prune` command — removes stale worktrees by age, with `--dry-run` (default) and `--apply` modes
- `-o`/`--output` flag on `git workspace up`, `git workspace init`, and `git workspace clone` for machine-readable path output
- `--detached` flag on `git workspace up` to skip `on_attach` hooks for headless/agent workflows
- `GIT_WORKSPACE_LOG_LEVEL` environment variable to enable debug/info/warning logging to stderr
- GitHub Actions: CI workflow (lint, type check, unit + integration tests) and PyPI publish on semver tag push
- Ruff (lint + format) and ty (type check) configured with pre-commit hooks
- `SKILL.md` to instruct agents on how to use this tool
- `[[copy]]` manifest directive — copies files from `.workspace/assets` into worktrees (idempotent on reset, atomic ignore sync shared with links)
- `GIT_WORKSPACE_NAME` environment variable hook injection
- Inline shell commands in hooks — entries that don't match a file in `.workspace/bin` are executed via `sh -c`

### Changed
- Minimum Python version lowered from 3.15 to 3.14
- Worktree age is derived from directory birthtime (`st_birthtime` on macOS, `st_ctime` fallback on Linux)

### Fixed
- `git fetch` now captures stderr, preventing a `NoneType` crash when no remote is configured
- Empty repository worktree creation falls back to `git worktree add --orphan` when no commits exist
- `_try_create_from_remote_branch` gracefully handles missing remotes instead of propagating `GitFetchError`

## [0.1.0] - 2026-04-07

Initial release. Core workspace model with `init`, `clone`, `up`, `down`, `reset`, `rm`, and `ls` commands.
