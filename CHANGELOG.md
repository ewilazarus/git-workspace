# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Fingerprint support — declare `[[fingerprint]]` blocks in `manifest.toml` to hash a set of files at the worktree root and expose the result as `GIT_WORKSPACE_FINGERPRINT_<NORMALIZED_NAME>` in hook and `exec` environments; supports `sha256` (default) and `md5` algorithms with configurable digest prefix length; `git workspace doctor` validates fingerprint config (name clashes, unsupported algorithms, path escapes, etc.)
- Placeholder substitution in copied assets — `{{ GIT_WORKSPACE_* }}` tokens are replaced with their environment variable values at copy time
- `git workspace exec <branch> -- <command>` — runs an arbitrary command inside a worktree; prompts to create the worktree first if it doesn't exist (`--force` skips the prompt); propagates the command's exit code
- `git workspace doctor` command — inspects the workspace for inconsistencies (missing asset sources, clashing targets, broken hook references, orphaned files, stale worktrees, and more); exits 1 on errors, 0 on warnings or clean
- `--version` global flag to print the installed version and exit
- PyPI publish workflow now triggers on PEP 440 pre-release tags (`a`, `b`, `rc`)
- `GIT_WORKSPACE_BIN` and `GIT_WORKSPACE_ASSETS` environment variables injected into hook execution environments
- `--plain` global flag and automatic TTY detection to fall back to plain text output in non-interactive terminals

### Removed
- `git workspace exec` command — removed; use shell subexpressions with `git workspace up --detached -o` to run commands inside a worktree
- `git workspace root` command — removed; use `git workspace up --output` or check `GIT_WORKSPACE_ROOT` from within a hook instead

### Changed
- **Breaking:** Hook lifecycle renamed to clarify two distinct lifetimes:
  - `on_activate` is removed; its per-`up` role is replaced by `on_attach` (interactive) or nothing (detached)
  - `on_deactivate` is renamed to `on_detach` — runs on `down` and at the start of `rm`
  - `on_remove` is renamed to `on_teardown` — runs on `rm`, after `on_detach`, before deletion
  - `on_setup` and `on_attach` are unchanged in name; `on_attach` is now the only session-start hook
  - `GIT_WORKSPACE_EVENT` values are now `ON_SETUP`, `ON_ATTACH`, `ON_DETACH`, and `ON_TEARDOWN`
  - **How to migrate:** rename `on_activate` entries into `on_attach` (if they need a terminal) or `on_setup` (if they are one-time setup); rename `on_deactivate` to `on_detach`; rename `on_remove` to `on_teardown`
- `git workspace up` no longer runs `on_activate`; it runs `on_setup` (first time only) and `on_attach` (unless `--detached`)
- `git workspace exec` provisions a missing worktree (runs `on_setup`) but does not run `on_attach` or `on_detach`
- Worktree lifecycle logic extracted into a dedicated `operations` module; CLI commands now delegate to named operations instead of inlining asset and hook orchestration
- `git workspace prune` no longer runs hooks — worktrees are force-removed directly
- Inline shell commands in hooks now run via the user's shell (`$SHELL`, defaulting to `sh`) instead of the system `sh`

## [0.5.0] - 2026-04-22

### Changed
- **Breaking:** `git workspace up <remote-branch>` now checks out the remote branch instead of silently creating a new one from `main` (bare clones omit the fetch refspec, so remote branches were never tracked)
- **Breaking:** `git workspace up <new-branch>` now forks from the latest remote base branch instead of a potentially stale local copy (forking from `origin/<base>` directly avoids the ref-lock when the base is already checked out in a worktree)

**How to fix:** Workspaces cloned before `v0.5.0` need to be cloned again using the new version

## [0.4.0] - 2026-04-19

### Added
- `overwrite` property on `[[copy]]` directives (default `true`). Setting `overwrite = false` seeds the file on first worktree creation and preserves local edits across `git workspace reset`.

### Changed
- Improved stderr output: structured sections with spinner-to-checkmark transitions, per-type hook progress bars, and distinct colours for asset and hook names
- Exception messages now include contextual details (paths, branch names, stderr output) and consistently start with a capital letter

### Fixed
- CI workflow no longer runs twice on PRs; `push` trigger is now restricted to `main`
- `pull_branch` now passes `--update-head-ok` to `git fetch` so it succeeds when the base branch is currently checked out

## [0.3.0] - 2026-04-16

### Added
- Increased `prune` unit test coverage

### Changed
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
