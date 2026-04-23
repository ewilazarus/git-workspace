<p align="center">
  <img src=".github/banner.png" width="800" />
</p>

<h3 align="center"><code>git-workspace</code></h3>
<h6 align="center">Local environments with zero friction.</h6>

<br/>

<p align="center">
  <a href="https://github.com/ewilazarus/git-workspace/actions/workflows/ci.yml"><img src="https://github.com/ewilazarus/git-workspace/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  &nbsp;
  <a href="https://github.com/ewilazarus/git-workspace/actions/workflows/pypi.yml"><img src="https://github.com/ewilazarus/git-workspace/actions/workflows/pypi.yml/badge.svg" alt="PyPI"></a>
</p>

<hr/>

`git-workspace` is an opinionated git plugin that wraps [git worktrees](https://git-scm.com/docs/git-worktree) with a lifecycle system — so switching between branches feels like switching between projects, not shuffling stashes.

#### The problem it solves

`git stash`, `git switch`, re-run your dev server, restore your editor tabs. Repeat twenty times a day.

With `git-workspace`, each branch lives in its own directory. You `up` into it, your environment is ready — dependencies installed, config files in place, hooks executed. You `down` out of it, your teardown scripts run. You come back tomorrow and everything is exactly where you left it.

#### Table of contents

- [Features](#features)
- [Demo](#demo)
- [How it works](#how-it-works)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Workspace manifest](#workspace-manifest)
- [Lifecycle hooks](#lifecycle-hooks)
- [Assets: links and copies](#assets-links-and-copies)
- [Pruning stale worktrees](#pruning-stale-worktrees)
- [Detached mode](#detached-mode)
- [Diagnosing a workspace](#diagnosing-a-workspace)
- [Debugging](#debugging)
- [Development](#development)

---

## Features

- 🌳 **Worktree-per-branch** — every branch gets its own directory; no more dirty working trees
- ⚡ **Lifecycle hooks** — run scripts on setup, activation, attachment, deactivation, and removal
- 🔗 **Symlink injection** — link dotfiles and config from a shared config repo into every worktree
- 📋 **File copying** — copy mutable config files that each worktree can edit independently
- 🔒 **Override assets** — replace tracked files with symlinks or copies without touching git history
- 📦 **Variables** — pass manifest-level and runtime variables into hooks as environment variables
- 🧭 **CWD-aware** — detects when you're already inside a workspace or worktree
- 🏗️ **Detached mode** — skip interactive hooks for headless, CI, or agent workflows
- 🧹 **Stale worktree pruning** — clean up old worktrees by age with dry-run preview
- 🩺 **Workspace diagnostics** — detect manifest errors, missing assets, broken hook references, and more
- 🎨 **Rich terminal UI** — styled output, progress bars, and sortable worktree tables
- 🗂️ **Config as code** — workspace configuration lives in its own git repo, versioned and shareable

---

## Demo

https://github.com/user-attachments/assets/27bf0e6e-ac8c-424e-b899-8601ac4d54b7

---

## How it works

A `git-workspace` workspace is a directory containing:

```
my-project/
├── .git/           ← bare git clone of your repository
├── .workspace/     ← clone of your config repository
│   ├── manifest.toml
│   ├── assets/     ← files to be linked or copied into worktrees
│   └── bin/        ← lifecycle hook scripts
├── main/           ← worktree for the main branch
├── feature/
│   └── my-feature/ ← worktree for feature/my-feature
└── ...
```

Each subdirectory is a fully functional git worktree. You work inside them like normal repositories.

---

## Installation

Requires Python 3.14+.

**With `uv` (recommended):**

```bash
uv tool install git-workspace-cli
```

**With `pip`:**

```bash
pip install git-workspace-cli
```

Once installed, `git workspace` is available as a git subcommand.

> [!WARNING]
> Ensure your `uv`/`pip` install path is in `$PATH`, so Git can locate the `git-workspace` executable.

---

## Quick start

**Start from an existing repository:**

```bash
git workspace clone https://github.com/you/your-repo.git
cd your-repo
cd $(git workspace up hotfix/urgent -o)
```

**Start a brand new project:**

```bash
mkdir my-project && cd my-project
git workspace init
cd $(git workspace up main -o)
```

You're now inside `my-project/main/` — a real git worktree on the `main` branch.

---

## Commands

> [!TIP]
> Use `git workspace --help` to explore all commands and flags in detail.

| Command | Description |
|---|---|
| `git workspace init` | Initialize a new workspace in the current directory |
| `git workspace clone` | Clone an existing repository into workspace format |
| `git workspace up` | Open a worktree, creating it if it doesn't exist |
| `git workspace down` | Deactivate a worktree and run teardown hooks |
| `git workspace reset` | Reapply copies, links, and re-run setup hooks |
| `git workspace rm` | Remove a worktree (branch is preserved) |
| `git workspace ls` | List all active worktrees with branch, path, and age |
| `git workspace prune` | Remove stale worktrees by age (dry-run by default) |
| `git workspace root` | Print workspace root path; exits 0 if inside a workspace, 1 otherwise |
| `git workspace doctor` | Inspect the workspace for inconsistencies |
| `git workspace edit` | Open the workspace config in your editor |

`[branch]` and `--root` let you operate on a workspace from anywhere in the file system, without needing to be inside it.

### Path output for automation

`init`, `clone`, and `up` accept an `-o` / `--output` flag that prints the resulting path to stdout and suppresses all other output. This makes them composable with shell subexpressions:

```bash
# jump straight into a new worktree in one command
cd $(git workspace up feat/my-feature -o)

# clone a repo and land inside it immediately
cd $(git workspace clone https://github.com/you/your-repo.git -o)

# use in scripts without worrying about hook output polluting the result
WORKTREE=$(git workspace up feat/experiment --detached -o)
code "$WORKTREE"
```

---

## Workspace manifest

The manifest lives at `.workspace/manifest.toml` and controls everything:

```toml
version = 1
base_branch = "main"

# Variables injected into every hook as GIT_WORKSPACE_VAR_*
[vars]
node-version = "22"
registry     = "https://registry.npmjs.org"

# Lifecycle hooks (.workspace/bin/ scripts and inline commands)
[hooks]
on_setup      = ["install_deps", "docker build . -t myproj:latest"]
on_activate   = ["load_env"]
on_attach     = ["open_editor"]
on_deactivate = ["save_state"]
on_remove     = ["clean_cache"]

# Symlinks applied to every worktree
[[link]]
source = "dotfile"
target = ".nvmrc"

[[link]]
source = "vscode-settings.json"
target = ".vscode/settings.json"
override = true

# File copies — each worktree gets its own mutable version
[[copy]]
source = "config.local.yaml"
target = "config.local.yaml"

# Automatic cleanup rules
[prune]
older_than_days  = 30
exclude_branches = ["main", "develop"]
```

---

## Lifecycle hooks

Each hook entry can be a script in `.workspace/bin/` or an inline shell command. If the entry matches a file in `.workspace/bin/`, it runs as a script; otherwise it's executed via `sh -c`. Both forms receive the following environment variables:

| Variable | Value |
|---|---|
| `GIT_WORKSPACE_ROOT` | Absolute path to the workspace root |
| `GIT_WORKSPACE_NAME` | Workspace root directory name |
| `GIT_WORKSPACE_WORKTREE` | Absolute path to the current worktree |
| `GIT_WORKSPACE_BRANCH` | Current branch name |
| `GIT_WORKSPACE_EVENT` | The lifecycle event that triggered the hook |
| `GIT_WORKSPACE_VAR_*` | All manifest and runtime variables |

### Hook execution order

| Event | When it runs |
|---|---|
| `on_setup` | After a worktree is first created, or on `reset` |
| `on_activate` | On every `up` (attached and detached) |
| `on_attach` | On `up` in interactive mode only (skipped with `--detached`) |
| `on_deactivate` | On `down` and `rm` |
| `on_remove` | On `rm`, after deactivation |

**Example hook** (`.workspace/bin/install_deps`):

```bash
#!/bin/sh
# hooks already run from the worktree root — no cd needed
node_version="$GIT_WORKSPACE_VAR_NODE_VERSION"
fnm use "$node_version" || fnm install "$node_version"
npm install
```

**Mix bin scripts and inline commands** in the same hook list:

```toml
[hooks]
on_setup = ["install_deps", "docker build . -t myproj:latest", "echo ready"]
```

Here `install_deps` runs `.workspace/bin/install_deps`, while `docker build . -t myproj:latest` and `echo ready` run as shell commands.

**Pass runtime variables** at call time with `-v`:

```bash
git workspace up feature/my-feature -v env=staging -v debug=true
```

---

## Assets: links and copies

Assets let you inject shared files — dotfiles, editor configs, secrets — into every worktree from your config repository. They live in `.workspace/assets/` and are applied automatically on `up` and `reset`.

### Links

Symbolic links from `.workspace/assets` into the worktree. The source asset is shared across all worktrees — editing the link edits the original.

```toml
[[link]]
source = "env.local"
target = ".env.local"
```

### Copies

File copies from `.workspace/assets` into the worktree. Each worktree gets its own independent file. Copies are idempotent — `reset` overwrites them with a fresh copy from the source.

```toml
[[copy]]
source = "config.local.yaml"
target = "config.local.yaml"
```

Set `overwrite = false` to seed the file once and preserve local edits across resets. The file is still created on the first `up`, but subsequent `reset` calls leave it untouched.

```toml
[[copy]]
source = "config.local.yaml"
target = "config.local.yaml"
overwrite = false
```

### Override mode

By default, asset targets are added to `.git/info/exclude` so they stay invisible to git. Set `override = true` to replace a tracked file instead — the target is marked with `git update-index --skip-worktree` before the asset is applied.

```toml
[[link]]
source = "vscode-settings.json"
target = ".vscode/settings.json"
override = true
```

---

## Pruning stale worktrees

Over time, worktrees accumulate. The `prune` command removes the ones you're no longer using:

```bash
# preview what would be removed (default)
git workspace prune --older-than-days 14

# actually remove them
git workspace prune --older-than-days 14 --apply
```

Pruning force-removes worktrees directly and does **not** run lifecycle hooks. Configure defaults in the manifest so you can just run `git workspace prune`:

```toml
[prune]
older_than_days  = 30
exclude_branches = ["main", "develop"]
```

---

## Detached mode

For CI pipelines, automation, or agent workflows where you don't want interactive hooks to fire:

```bash
git workspace up main --detached
```

This runs `on_setup` and `on_activate` but skips `on_attach`. Combine with `-o` for fully machine-readable output:

```bash
WORKTREE=$(git workspace up main --detached -o)
```

---

## Diagnosing a workspace

`git workspace doctor` inspects the workspace configuration and reports anything that would cause commands to fail or behave unexpectedly.

```bash
git workspace doctor
```

If everything is in order:

```
✓  Workspace is healthy.
```

Otherwise it lists findings by severity:

```
✗  Link source 'dotfile' does not exist in assets/
⚠  Script 'bin/old_script.sh' is not referenced by any hook
⚠  base_branch 'develop' does not resolve to any local or remote ref
```

**Errors** (✗) indicate problems that will break `up`, `reset`, or hooks. **Warnings** (⚠) indicate configuration that is suspicious but may be intentional — for example, a hook entry that looks like a bin script name but has no matching file (it may be an ad-hoc inline command).

The command exits 1 if any errors are found, 0 if the workspace is clean or has warnings only.

### What it checks

**Errors:**

| Check | Description |
|---|---|
| Manifest not readable / invalid TOML | The manifest file cannot be opened or parsed |
| Unsupported manifest version | `version` is higher than this tool supports |
| Missing asset source | A `[[link]]` or `[[copy]]` source file does not exist in `assets/` |
| Clashing asset targets | Two entries share the same `target` path |
| Escaping asset target | A `target` path traverses outside the worktree root (e.g. `../../`) |
| Variable name collision | Two `[vars]` keys normalize to the same `GIT_WORKSPACE_VAR_*` name |

**Warnings:**

| Check | Description |
|---|---|
| Missing bin script | A whitespace-free hook entry has no matching file in `bin/` |
| Non-executable bin script | A matching `bin/` file exists but is not executable |
| Empty hook entry | A hook list contains an empty or whitespace-only string |
| Duplicate hook entry | The same entry appears more than once in the same hook event |
| Orphaned bin script | A file in `bin/` is not referenced by any hook |
| Orphaned asset | A file in `assets/` is not referenced by any `[[link]]` or `[[copy]]` |
| Unknown base branch | `base_branch` does not resolve to any local or remote ref |
| Stale worktree | A git-registered worktree's directory no longer exists on disk |

---

## Debugging

Set `GIT_WORKSPACE_LOG_LEVEL` to get diagnostic output on stderr:

```bash
GIT_WORKSPACE_LOG_LEVEL=DEBUG git workspace up main
```

Supported levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Logging is silent by default.

---

## Development

**Clone and set up:**

```bash
git clone https://github.com/ewilazarus/git-workspace.git
cd git-workspace
uv sync
```

**Run the tests:**

```bash
uv run pytest
```

The test suite includes both unit tests and integration tests. Integration tests spin up real git repositories in temporary directories — no mocking.

**Lint and type check:**

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
```

**Project layout:**

```
src/git_workspace/
├── cli/commands/   ← one file per command
├── assets.py       ← symlink and copy management
├── doctor.py       ← workspace diagnostic checks
├── errors.py       ← exception hierarchy
├── git.py          ← subprocess wrappers for git
├── hooks.py        ← lifecycle hook runner
├── manifest.py     ← manifest parsing
├── worktree.py     ← worktree model
└── workspace.py    ← top-level workspace model
```

---

## Disclaimer

I built `git-workspace` because it fits *my* way of working. The worktree-per-branch model, the hook lifecycle, the asset injection — these are the exact primitives I was missing.

If it turns out to be useful to you too, [consider supporting the project](https://buymeacoffee.com/simiosoft). Contributions and feedback are welcome!

> [!NOTE]
> Developed and verified on macOS. Linux support is expected but untested. Windows is not supported.

---

*Built with [Typer](https://typer.tiangolo.com), [Rich](https://rich.readthedocs.io), and a deep appreciation for git worktrees.*
