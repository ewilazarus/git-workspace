# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 0.2.0

### Added
- Added `SKILL.md` to instruct agents on how to use this tool
- Rich terminal UI: live-streaming hook output, progress bar for link application, styled branch/path colours
- `gw ls` renders a Rich table with Branch, Path, and Age columns, sorted by age then alphabetically
- `gw root` command — prints workspace root path and exits 0/1, intended for agent/scripting use
- `gw prune` command — removes stale worktrees by age, with `--dry-run` (default) and `--apply` modes
- `-o`/`--output` flag on `gw up`, `gw init`, and `gw clone` for machine-readable path output
- `--detached` flag on `gw up` to skip `on_attach` hooks for headless/agent workflows
- `GIT_WORKSPACE_LOG_LEVEL` environment variable to enable debug/info/warning logging to stderr
- GitHub Actions: CI workflow (lint, type check, unit + integration tests) and PyPI publish on semver tag push
- Ruff (lint + format) and ty (type check) configured with pre-commit hooks

### Changed
- Worktree age is derived from directory birthtime (`st_birthtime` on macOS, `st_ctime` fallback on Linux)

### Fixed
- `git fetch` now captures stderr, preventing a `NoneType` crash when no remote is configured
- Empty repository worktree creation falls back to `git worktree add --orphan` when no commits exist
- `_try_create_from_remote_branch` gracefully handles missing remotes instead of propagating `GitFetchError`

## [0.1.0] - 2026-04-07

Initial release. Core workspace model with `init`, `clone`, `up`, `down`, `reset`, `rm`, and `ls` commands.
