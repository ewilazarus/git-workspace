# git-workspace

> One repo. Many branches. Zero context-switching friction.

`git-workspace` is an opinionated CLI that wraps [git worktrees](https://git-scm.com/docs/git-worktree) with a lifecycle system — so switching between branches feels like switching between projects, not shuffling stashes.

<!-- DEMO VIDEO PLACEHOLDER -->

---

## The problem it solves

`git stash`, `git switch`, re-run your dev server, restore your editor tabs. Repeat twenty times a day.

With `git-workspace`, each branch lives in its own directory. You `up` into it, your environment is ready. You `down` out of it, your teardown scripts run. You come back tomorrow and everything is exactly where you left it.

---

## Features

- 🌳 **Worktree-per-branch** — every branch gets its own directory; no more dirty working trees
- ⚡ **Lifecycle hooks** — run scripts on setup, activation, attachment, deactivation, and removal
- 🔗 **Symlink injection** — link dotfiles and config from a shared config repo into every worktree automatically
- 🔒 **Override linking** — replace tracked files with symlinks without touching git history
- 📦 **Variables** — pass manifest-level and runtime variables into hooks as environment variables
- 🧭 **CWD-aware** — omit `--root` and `[branch]` when you're already inside a workspace or worktree
- 🏗️ **Detached mode** — skip interactive hooks for headless, CI, or agent workflows
- 🗂️ **Config as code** — workspace configuration lives in its own git repo, versioned and shareable

---

## How it works

A `git-workspace` workspace is a directory containing:

```
my-project/
├── .git/           ← bare git clone of your repository
├── .workspace/     ← clone of your config repository
│   ├── manifest.toml
│   ├── assets/     ← files to be linked into worktrees
│   └── bin/        ← lifecycle hook scripts
├── main/           ← worktree for the main branch
├── feature/
│   └── my-feature/ ← worktree for feature/my-feature
└── ...
```

Each subdirectory is a fully functional git worktree. You work inside them like normal repositories.

---

## Installation

Requires Python 3.15+.

**With `uv` (recommended):**

```bash
uv tool install git-workspace-cli
```

**With `pip`:**

```bash
pip install git-workspace-cli
```

Once installed, `git workspace` is available as a git subcommand.

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

| Command | Description |
|---|---|
| `git workspace init` | Initialize a new workspace in the current directory |
| `git workspace clone <url>` | Clone an existing repository into workspace format |
| `git workspace up [branch]` | Open a worktree, creating it if it doesn't exist |
| `git workspace down [branch]` | Deactivate a worktree and run teardown hooks |
| `git workspace reset [branch]` | Reapply links and re-run setup hooks |
| `git workspace rm [branch]` | Remove a worktree (branch is preserved) |
| `git workspace list` | List all active worktrees |
| `git workspace edit` | Open the workspace config in your editor |

`[branch]` and `--root` can always be omitted when your shell is already inside a workspace or worktree.

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
registry = "https://registry.npmjs.org"

# Lifecycle hooks (scripts in .workspace/bin/)
[hooks]
on_setup      = ["install_deps"]
on_activate   = ["load_env"]
on_attach     = ["open_editor"]
on_deactivate = ["save_state"]
on_remove     = ["clean_cache"]

# Symlinks applied to every worktree
[[link]]
source = "dotfile"       # path inside .workspace/assets/
target = ".nvmrc"        # path inside the worktree root

[[link]]
source = "vscode-settings.json"
target = ".vscode/settings.json"
override = true          # replaces an already-tracked file
```

---

## Lifecycle hooks

Hooks are executable scripts stored in `.workspace/bin/`. They run with a rich set of environment variables:

| Variable | Value |
|---|---|
| `GIT_WORKSPACE_ROOT` | Absolute path to the workspace root |
| `GIT_WORKSPACE_WORKTREE` | Absolute path to the current worktree |
| `GIT_WORKSPACE_BRANCH` | Current branch name |
| `GIT_WORKSPACE_EVENT` | The lifecycle event that triggered the hook |
| `GIT_WORKSPACE_VAR_*` | All manifest and runtime variables |

**Example hook** (`.workspace/bin/install_deps`):

```bash
#!/bin/sh
# hooks already run from the worktree root — no cd needed
node_version="$GIT_WORKSPACE_VAR_NODE_VERSION"
fnm use "$node_version" || fnm install "$node_version"
npm install
```

**Pass runtime variables** at call time with `-v`:

```bash
git workspace up feature/my-feature -v env=staging -v debug=true
```

---

## Symlink linking

Links let you inject shared files — dotfiles, editor configs, secrets — into every worktree from your config repository.

- **Regular links** are added to `.git/info/exclude` so they stay invisible to git.
- **Override links** (`override = true`) use `git update-index --skip-worktree` to silently replace a tracked file with your symlink.

```toml
[[link]]
source = "env.local"
target = ".env.local"

[[link]]
source = "vscode-settings.json"
target = ".vscode/settings.json"
override = true
```

---

## Detached mode

For CI pipelines, automation, or agent workflows where you don't want interactive hooks to fire:

```bash
git workspace up main --detached
```

This runs `on_setup` and `on_activate` but skips `on_attach`.

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

**Project layout:**

```
src/git_workspace/
├── cli/commands/   ← one file per command
├── assets.py       ← symlink management
├── errors.py       ← exception hierarchy
├── git.py          ← subprocess wrappers for git
├── hooks.py        ← lifecycle hook runner
├── manifest.py     ← manifest parsing
├── worktree.py     ← worktree model
└── workspace.py    ← top-level workspace model
```

---

## Disclaimer

I built `git-workspace` because it fits *my* way of working. The worktree-per-branch model, the hook lifecycle, the symlink injection — these are the exact primitives I was missing.

If it turns out to be useful to you too, that's a bonus. Contributions and feedback are welcome, but this tool will always be shaped first by how I want to use it.

---

*Built with [Typer](https://typer.tiangolo.com), [structlog](https://www.structlog.org), and a deep appreciation for git worktrees.*
