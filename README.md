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

<details>
<summary><i>Table of contents</i></summary>
<br/>

- [Features](#features)
- [Demo](#demo)
- [How it works](#how-it-works)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Workspace manifest](#workspace-manifest)
- [Lifecycle hooks](#lifecycle-hooks)
- [Fingerprints](#fingerprints)
- [Assets: links and copies](#assets-links-and-copies)
- [Pruning stale worktrees](#pruning-stale-worktrees)
- [Detached mode](#detached-mode)
- [Diagnosing a workspace](#diagnosing-a-workspace)
- [Debugging](#debugging)
- [Development](#development)
</details>

---

## Features

- 🌳 **Worktree-per-branch** — every branch gets its own directory; no more dirty working trees
- 🪝 **Lifecycle hooks** — run scripts on setup, attach, detach, and teardown
- 🔗 **Symlink injection** — link dotfiles and config from a shared config repo into every worktree
- 📋 **File copying** — copy mutable config files that each worktree can edit independently
- 🔒 **Override assets** — replace tracked files with symlinks or copies without touching git history
- 📦 **Variables** — pass manifest-level and runtime variables into hooks as environment variables
- 🔏 **Fingerprints** — hash worktree files and expose the digest for further processing
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

<br/>

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

<br/>

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
| `git workspace doctor` | Inspect the workspace for inconsistencies |
| `git workspace edit` | Open the workspace config in your editor |

`[branch]` and `--root` let you operate on a workspace from anywhere in the file system, without needing to be inside it.

---

## Workspace manifest

The manifest lives at `.workspace/manifest.toml` and controls everything. For example:

```toml
version = 1
base_branch = "main"

# Variables injected into every hook as GIT_WORKSPACE_VAR_*
[vars]
node-version = "22"
registry     = "https://registry.npmjs.org"

# Lifecycle hooks (.workspace/bin/ scripts and inline commands)
[[hooks.on_setup]]
commands = ["install_deps", "docker build . -t myproj:latest"]

[[hooks.on_attach]]
commands = ["open_editor"]

[[hooks.on_detach]]
commands = ["save_state"]

[[hooks.on_teardown]]
commands = ["clean_cache"]

# Symlinks applied to every worktree
[[link]]
source = "vscode-settings.json"
target = ".vscode/settings.json"

# File copies — each worktree gets its own mutable version
[[copy]]
source = "config.local.yaml"
target = "config.local.yaml"
```

---

## Lifecycle hooks

Each hook entry can be a script in `.workspace/bin/` or an inline shell command. If the entry matches a file in `.workspace/bin/`, it runs as a script; otherwise it's executed via the user shell. 

### Hook execution order

Hooks come in two pairs that map to the two lifetimes a worktree has:

- **Worktree lifetime** — `on_setup` and `on_teardown` bracket the full existence of the worktree directory.
- **Coding Session lifetime** — `on_attach` and `on_detach` bracket each interactive session inside it.

  | Event | When it runs |
  |---|---|
  | `on_setup` | After a worktree is first created, or on `reset` |
  | `on_attach` | On `up` in interactive mode (skipped with `--detached`) |
  | `on_detach` | On `down` and at the start of `rm` |
  | `on_teardown` | On `rm`, after `on_detach`, before the directory is deleted |

<br/>

> [!WARNING]
> Implement `on_attach` and `on_detach` hooks as idempotent operations. `git-workspace` treats these lifecycle events as potentially repeatable rather than strictly linear, accounting for edge cases where a session is interrupted before completion.

<br/>

<details>
<summary><i>Environment variables</i></summary>
<br/>

The following environment variables are available during hook execution:

| Variable | Value |
|---|---|
| `GIT_WORKSPACE_ROOT` | Absolute path to the workspace root |
| `GIT_WORKSPACE_NAME` | Workspace root directory name |
| `GIT_WORKSPACE_WORKTREE` | Absolute path to the current worktree |
| `GIT_WORKSPACE_BRANCH` | Current branch name |
| `GIT_WORKSPACE_EVENT` | The lifecycle event that triggered the hook |
| `GIT_WORKSPACE_VAR_*` | All manifest and runtime variables |
| `GIT_WORKSPACE_FINGERPRINT_*` | Content hashes computed from `[[fingerprint]]` file sets |

</details>

<details>
<summary><i>Conditional execution</i></summary>
<br/>

Each hook event can have multiple `[[hooks.<event>]]` groups. A group only runs when its `conditions` block matches the effective branch. Groups with no `conditions` always run. Groups are evaluated top-to-bottom in manifest order.

#### Supported conditions

| Key | Behaviour |
|---|---|
| `if_branch_matches` | Run only when the branch matches the glob pattern |
| `if_branch_not_matches` | Run only when the branch does **not** match the glob pattern |

Both conditions use POSIX glob syntax (`*`, `?`, `[...]`). When both keys are present they are AND-ed: the group runs only when both hold.

**Example:**

```toml
# Always runs — no conditions
[[hooks.on_setup]]
commands = ["npm install"]

# Only on your own branches
[[hooks.on_setup]]
conditions = { if_branch_matches = "gabriel/*" }
commands = ["tmux attach -t MYSESSION"]

# Only on other branches
[[hooks.on_setup]]
conditions = { if_branch_not_matches = "gabriel/*" }
commands = ["echo not my branch"]

# Only on gabriel/* but not wip branches (AND)
[[hooks.on_setup]]
conditions = { if_branch_matches = "gabriel/*", if_branch_not_matches = "gabriel/wip-*" }
commands = ["start_long_running_task"]
```

#### Impersonating a branch with `--as`

All hook-running commands (`up`, `down`, `reset`, `rm`) accept `-a`/`--as <branch>` to override which branch is used when evaluating hook conditions. The real `GIT_WORKSPACE_BRANCH` environment variable and git state are **not** affected.

```bash
# Run hooks as if this were a gabriel/* branch, even though the real branch is feat/my-feature
git workspace up feat/my-feature --as gabriel/my-feature
```

This is useful when a shared feature branch should trigger the same hooks as a personal branch, or when scripting against a branch that doesn't exist yet.

</details>

---

## Fingerprints

Fingerprints let you compute a short content hash over a set of files in the worktree and expose it as an environment variable. This gives hooks a cheap way to detect whether their inputs have changed — for example, only re-run `npm install` when `package-lock.json` changes, or only rebuild a Docker image when the Dockerfile or dependency files change.

Declare fingerprints as `[[fingerprint]]` blocks in the manifest:

```toml
[[fingerprint]]
name = "docker-deps"
files = [
    "Dockerfile",
    "package.json",
    "package-lock.json",
]
algorithm = "sha256"  # optional; default: sha256
length = 12           # optional; default: 12
```

Each fingerprint is exposed as `GIT_WORKSPACE_FINGERPRINT_<NORMALIZED_NAME>` (same normalization as vars — uppercase, non-alphanumeric replaced by `_`). The above example produces `GIT_WORKSPACE_FINGERPRINT_DOCKER_DEPS`.

Fingerprints are recomputed on every `up`, `reset`, `down`, and `rm` invocation. Files are looked up relative to the worktree root; a missing or unreadable file contributes its path and the literal marker `NULL` to the hash rather than failing.

<details>
<summary><i>Usage example</i></summary>
<br/>

```sh
#!/bin/sh

state_file="$GIT_WORKSPACE_ROOT/.fingerprint-docker-deps"
current="$GIT_WORKSPACE_FINGERPRINT_DOCKER_DEPS"
previous=$(cat "$state_file" 2>/dev/null || echo "")

if [ "$current" != "$previous" ]; then
    docker build . -t myapp
    echo "$current" > "$state_file"
fi
```

</details>

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

<details>
<summary><i>Overwrite control</i></summary>
<br/>

Set `overwrite = false` to seed the file once and preserve local edits across resets. The file is still created on the first `up`, but subsequent `reset` calls leave it untouched.

```toml
[[copy]]
source = "config.local.yaml"
target = "config.local.yaml"
overwrite = false
```

</details>

<details>
<summary><i>Placeholders</i></summary>
<br/>

Text files in `.workspace/assets/` can contain `{{ GIT_WORKSPACE_* }}` placeholders. When the file is copied, each placeholder is replaced with the corresponding value from the environment — the same variables available to hooks, including manifest, runtime, and fingerprint vars.

```
# .workspace/assets/config.local.yaml
branch: {{ GIT_WORKSPACE_BRANCH }}
worktree: {{ GIT_WORKSPACE_WORKTREE }}
env: {{ GIT_WORKSPACE_VAR_ENV }}
```

After `git workspace up feature/my-feature -v env=staging`, the copied file becomes:

```yaml
branch: feature/my-feature
worktree: /path/to/workspace/feature/my-feature
env: staging
```

Unknown placeholders are left verbatim. Binary files are copied as-is without substitution. When the source is a directory, substitution is applied to every text file inside it.

</details>

### Override mode

By default, asset targets are added to `.git/info/exclude` so they stay invisible to git. Set `override = true` to replace a tracked file instead — the target is marked with `git update-index --skip-worktree` before the asset is applied.

```toml
[[link]]  # or [[copy]]
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

This runs `on_setup` (on first creation only) but skips `on_attach`. Combine with `-o` for fully machine-readable output:

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

<details>
<summary><i>Checks</i></summary>
<br/>

**Errors:**

| Check | Description |
|---|---|
| Manifest not readable / invalid TOML | The manifest file cannot be opened or parsed |
| Unsupported manifest version | `version` is higher than this tool supports |
| Missing asset source | A `[[link]]` or `[[copy]]` source file does not exist in `assets/` |
| Clashing asset targets | Two entries share the same `target` path |
| Escaping asset target | A `target` path traverses outside the worktree root (e.g. `../../`) |
| Variable name collision | Two `[vars]` keys normalize to the same `GIT_WORKSPACE_VAR_*` name |
| Fingerprint name collision | Two `[[fingerprint]]` names normalize to the same `GIT_WORKSPACE_FINGERPRINT_*` name |
| Empty fingerprint name | A `[[fingerprint]]` has an empty or whitespace-only `name` |
| Escaping fingerprint file | A `files` entry traverses outside the worktree root (e.g. `../../`) |
| Unsupported fingerprint algorithm | `algorithm` is not `sha256` or `md5` |
| Invalid fingerprint length | `length` is zero or negative |

**Warnings:**

| Check | Description |
|---|---|
| Missing bin script | A whitespace-free hook entry has no matching file in `bin/` |
| Non-executable bin script | A matching `bin/` file exists but is not executable |
| Empty hook entry | A hook list contains an empty or whitespace-only string |
| Duplicate hook entry | The same entry appears more than once in the same hook event |
| Orphaned bin script | A file in `bin/` is not referenced by any hook |
| Orphaned asset | A file in `assets/` is not referenced by any `[[link]]` or `[[copy]]` |
| Unknown copy placeholder | A `{{ GIT_WORKSPACE_* }}` placeholder in a copy asset is not a base variable, manifest var, or fingerprint |
| Unknown base branch | `base_branch` does not resolve to any local or remote ref |
| Stale worktree | A git-registered worktree's directory no longer exists on disk |
| Fingerprint/var name overlap | A `[[fingerprint]]` name and a `[vars]` key normalize the same (they use different env prefixes, but may be confusing in templates) |
| Empty fingerprint files list | A `[[fingerprint]]` has no entries in `files` |
| Duplicate fingerprint file | The same file path appears more than once within one `[[fingerprint]]` |
| Fingerprint length exceeds digest | `length` is larger than the algorithm's full digest size; the full digest is used |

</details>

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
uv run pre-commit install
```

**Run the tests:**

```bash
uv run pytest
```

The test suite includes both unit tests and integration tests. Integration tests spin up real git repositories in temporary directories — no mocking.

<details>
<summary><i>Lint and type check</i></summary>
<br/>

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run ty check src/
```

</details>

<details>
<summary><i>Project layout</i></summary>
<br/>

```
src/git_workspace/
├── cli/commands/   ← one file per command
├── assets.py       ← symlink and copy management
├── doctor.py       ← workspace diagnostic checks
├── env.py          ← GIT_WORKSPACE_* environment variable construction
├── errors.py       ← exception hierarchy
├── fingerprint.py  ← worktree file hashing and fingerprint env var computation
├── git.py          ← subprocess wrappers for git
├── hooks.py        ← hook logic and execution
├── manifest.py     ← manifest parsing
├── operations.py   ← lifecycle orchestration
├── ui.py           ← ui-related logic
├── utils.py        ← general logic that doesn't fit elsewhere
├── workspace.py    ← top-level workspace model
└── worktree.py     ← worktree model
```

</details>

---

## Disclaimer

I built `git-workspace` because it fits *my* way of working. The worktree-per-branch model, the hook lifecycle, the asset injection — these are the exact primitives I was missing.

If it turns out to be useful to you too, [consider supporting the project](https://buymeacoffee.com/simiosoft). Contributions and feedback are welcome!

<br/>

> [!NOTE]
> Developed and verified on macOS. Linux support is expected but untested. Windows is not supported.

---

*Built with [Typer](https://typer.tiangolo.com), [Rich](https://rich.readthedocs.io), and a deep appreciation for git worktrees.*
