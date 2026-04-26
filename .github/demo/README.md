# git-workspace demo

A scripted [VHS](https://github.com/charmbracelet/vhs) recording that walks
through the most notable features of `git-workspace` in under two minutes.
Re-render it whenever the CLI's UI changes — no more re-recording by hand.

## Re-rendering

```bash
cd .github/demo
vhs demo.tape
```

`demo.gif` is written next to the tape. The tape's hidden bootstrap rebuilds
a throwaway workspace at `~/git-workspace-demo` on every run, so the
recording is reproducible from a clean state.

Requirements: `vhs`, `git`, `uv`, `nvim`. The tape uses `uv run` against this
repo's source tree, so the recording always reflects the current branch — not
whatever version of `git-workspace-cli` is installed globally.

## What you can edit

| File | Purpose |
| --- | --- |
| `demo.tape` | Recording script — pacing, commands, terminal settings |
| `setup.sh` | Builds the throwaway workspace in `~/git-workspace-demo` |
| `workspace/manifest.toml` | Manifest the demo shows off |
| `workspace/bin/*` | Hook scripts whose narration appears on screen |
| `workspace/assets/*` | Linked / copied assets the demo inspects |

Hook scripts use `echo` + `sleep` to narrate features as they fire. Add a
line, bump the sleep, re-render — the gif picks it up.
