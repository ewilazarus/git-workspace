# git-workspace VHS demo
# Render with:  vhs demo.tape
#
# Prerequisites: vhs, git, uv, nvim on PATH.
# The hidden setup block builds a fresh playground at ~/git-workspace-demo
# from .github/demo/workspace/ on every run; the visible recording then
# walks through the most notable features.

Output demo.gif

Require git
Require uv
Require nvim

Set Shell      bash
Set FontSize   16
Set Width      1280
Set Height     720
Set TypingSpeed 50ms
Set Theme      "Catppuccin Mocha"
Set Padding    20

# ────────────────────────────────────────────────────────────────────────────
# Hidden bootstrap — never visible in the recording
# ────────────────────────────────────────────────────────────────────────────
Hide
Type "bash setup.sh > /tmp/gw-demo-setup.log 2>&1"
Enter
Sleep 10s
Type 'export PATH="$HOME/git-workspace-demo/.shim:$PATH"'
Enter
Type "export PS1='> '"
Enter
Type "export EDITOR=nvim"
Enter
Type "cd ~/git-workspace-demo"
Enter
Type "clear"
Enter
Show

# ────────────────────────────────────────────────────────────────────────────
# Intro — set the stage
# ────────────────────────────────────────────────────────────────────────────
Type "# git-workspace — every branch is its own project."
Sleep 1s
Enter
Sleep 2s

# ────────────────────────────────────────────────────────────────────────────
# Workspace layout
# ────────────────────────────────────────────────────────────────────────────
Type "ls -al"
Enter
Sleep 4s

Type "# .workspace/ holds the manifest, hooks, and assets."
Sleep 1s
Enter
Sleep 1500ms

Type "git workspace ls"
Enter
Sleep 4s

# ────────────────────────────────────────────────────────────────────────────
# The manifest — open it in nvim
# ────────────────────────────────────────────────────────────────────────────
Type "git workspace edit"
Enter
Sleep 2s
Type ":e .workspace/manifest.toml"
Enter
Sleep 14s
Type ":qa!"
Enter
Sleep 1s
Hide
Type "clear"
Enter
Show

# ────────────────────────────────────────────────────────────────────────────
# Activate a new branch — hooks narrate themselves while it runs
# ────────────────────────────────────────────────────────────────────────────
Type "# Activate feat/demo. Hooks fire, assets are copied, env is ready."
Sleep 1s
Enter
Sleep 1s

Type "cd $(git workspace up feat/demo -o)"
Enter
Sleep 13s

# ────────────────────────────────────────────────────────────────────────────
# Inspect the new worktree
# ────────────────────────────────────────────────────────────────────────────
Type "ls -al"
Enter
Sleep 4s

Type "# config.local.yaml was templated with {{ GIT_WORKSPACE_* }} placeholders."
Sleep 1s
Enter
Sleep 1500ms

Type "cat config.local.yaml"
Enter
Sleep 6s

Type "# Linked + copied files are invisible to git — no risk of leaking."
Sleep 1s
Enter
Sleep 1500ms

Type "git status"
Enter
Sleep 4s

# ────────────────────────────────────────────────────────────────────────────
# Back to the root — show both worktrees registered
# ────────────────────────────────────────────────────────────────────────────
Type "cd -"
Enter
Sleep 1s
Type "git workspace ls"
Enter
Sleep 4s
Hide
Type "clear"
Enter
Show

# ────────────────────────────────────────────────────────────────────────────
# Doctor finds inconsistencies and heals them
# ────────────────────────────────────────────────────────────────────────────
Type "git workspace doctor"
Enter
Sleep 4s

Type "git workspace doctor --fix --yes"
Enter
Sleep 5s

# ────────────────────────────────────────────────────────────────────────────
# Outro
# ────────────────────────────────────────────────────────────────────────────
Type "# Branches as projects. github.com/ewilazarus/git-workspace"
Sleep 1s
Enter
Sleep 4s
