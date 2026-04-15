---
name: git-workspace
description: Use when the user wants to work on a feature, hotfix, or any other branch
---

## What is git-workspace

A git plugin that manages isolated development environments on top of git worktrees. Each branch gets its own fully configured environment — dependencies installed, configuration files applied, environment variables loaded, lifecycle hooks executed. All commands are invoked as `git workspace <command>`.

## When to use this skill

Use `git workspace` commands when any of these apply:
- The user wants to work on a feature, hotfix, or any other branch
- The user mentions workspaces, environments, or spinning up a branch context

Standard git operations (commit, push, pull, rebase, merge) always use plain `git` regardless.

## Typical workflow

```
1. git workspace root                        # exit 0 → workspace, exit 1 → use plain git (checkout, switch, worktree)
2. git workspace up <branch> --detached -o   # activate branch
3. git pull / commit / push                  # standard git inside $WORKTREE
4. git workspace reset <branch>              # after pull/merge, reapply environment
```

## Activating a branch

```bash
WORKTREE=$(git workspace up <branch> --detached -o)
```

- `--detached` skips interactive hooks not meant for agents
- `-o` prints the worktree path to stdout and suppresses all other output
- Use `$WORKTREE` as the working directory for all subsequent operations on that branch

`up` installs dependencies, applies configuration files and symlinks, loads environment variables, and runs any other setup the human has defined. Do not replicate this with raw `git worktree` commands — you will produce an incomplete environment.

## Resetting a branch

```bash
git workspace reset <branch>
```

Reapplies configuration, symlinks, and setup hooks after a pull or merge so the environment reflects the updated branch state. Do not call after `git workspace up` — `up` already performs this setup.

## Constraints

- Always run `git workspace root` before any other `git workspace` command
- Always pass `--detached` and `-o` to `git workspace up`
- Never call `git worktree` directly inside a workspace
