# git-workspace herdr plugin

Prepares git-workspace worktrees automatically when [herdr](https://herdr.dev)
creates or opens them: on `worktree.created` / `worktree.opened` the plugin
runs `git workspace prepare <path>`, so copies, links, and `on_setup` hooks
are applied no matter which side initiated the worktree.

It also registers two actions:

| Action | Runs |
|---|---|
| **Prepare worktree** | `git workspace prepare` for the current worktree |
| **Re-run worktree preparation** | `git workspace prepare --force` |

## Install

```bash
herdr plugin link /path/to/git-workspace/integrations/herdr
```

or straight from GitHub:

```bash
herdr plugin install ewilazarus/git-workspace/integrations/herdr
```

Requires `git-workspace` on `PATH` (or `GIT_WORKSPACE_BIN` pointing at it)
and herdr ≥ 0.7.0.

## Behavior

- Repositories without a `.workspace/manifest.toml` are skipped silently —
  herdr fires worktree events for every repo it manages.
- Already-prepared worktrees are a no-op (`prepare` checks lifecycle state).
- When `git workspace up --backend herdr` created the worktree itself, the
  plugin detects the in-flight preparation (exit code 75, lock contention)
  and skips — the creator finishes the job.
- Failures surface as a herdr notification with the retry command; full
  output is in `herdr plugin log list --plugin git-workspace`.

## Design

The plugin is deliberately thin: it only resolves the worktree path from the
event payload and shells out to `git workspace prepare`. It parses no project
configuration, applies no assets, runs no hooks directly, and keeps no state —
all lifecycle rules live in git-workspace itself.
